#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2012 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    ..........................................
#
#    Modified by idleloop@yahoo.com: 2017, 2018
#

import re
import json
import urllib2
import time
from random import randint
import HTMLParser

try:
    import xbmc
    import xbmcgui
    # //kodi.wiki/index.php?title=Add-on:Parsedom_for_xbmc_plugins
    from CommonFunctions import parseDOM, stripTags, replaceHTMLCodes
    XBMC_MODE = True
except ImportError:
    from parsedom import parseDOM, stripTags
    XBMC_MODE = False    

RETRY_TIME = 5.0

ALL_SCRAPERS = (
    'TheBigPictures',
    'AtlanticInFocus',
    'TotallyCoolPix',
    'NewYorkTimesLens',
    'Reddit',
)


class BasePlugin(object):

    _title = ''
    _id = 0

    def __init__(self, _id):
        self._albums = []
        self._photos = {}
        self._id = _id
        self._parser = HTMLParser.HTMLParser()

    def get_albums(self):
        return self._albums or self._get_albums()

    def get_photos(self, album_url):
        return self._photos.get(album_url) or self._get_photos(album_url)

    def _get_albums(self):
        raise NotImplementedError

    def _get_photos(self, album_url):
        raise NotImplementedError

    def _get_html(self, url, retries=5):
        self.log('_get_html opening url "%s"' % url)
        req = urllib2.Request(url, None, { 'User-Agent' : 'Mozilla/5.0' })
        html = ''
        retry_counter=0
        while True:
            try:
                html = urllib2.urlopen(req).read()
                self.log('_get_html received %d bytes' % len(html))
                break
            except urllib2.HTTPError as ex:
                self.log('_get_html error: %s' % ex)
                if (re.match(r'HTTP Error 4.+', str(ex))):
                    raise
                if XBMC_MODE:
                    dialog = xbmcgui.Dialog()
                    dialog.notification( 'The Big Picture',
                        'waiting for remote server ...', 
                        xbmcgui.NOTIFICATION_INFO, int(RETRY_TIME*5000) )
                retry_counter += retry_counter
                time.sleep(RETRY_TIME + randint(0, 2*retries))
                pass
            if retry_counter >= retries:
                break
        return html

    def _collapse(self, iterable):
        return u''.join([e.string.strip() for e in iterable if e.string])

    @property
    def title(self):
        return self._title

    def log(self, msg):
        if XBMC_MODE:
            try:
                xbmc.log('TheBigPictures ScraperPlugin[%s]: %s' % (
                    self.__class__.__name__, msg
                #))
                ), level=xbmc.LOGNOTICE) # https://forum.kodi.tv/showthread.php?tid=324570
            except UnicodeEncodeError:
                xbmc.log('TheBigPictures ScraperPlugin[%s]: %s' % (
                    self.__class__.__name__, msg.encode('utf-8', 'ignore')
                #))
                ), level=xbmc.LOGNOTICE) # https://forum.kodi.tv/showthread.php?tid=324570
        else:
            try:
                print('TheBigPictures ScraperPlugin[%s]: %s' % (
                    self.__class__.__name__, msg
                ))
            except UnicodeEncodeError:
                print('TheBigPictures ScraperPlugin[%s]: %s' % (
                    self.__class__.__name__, msg.encode('utf-8', 'ignore')
                ))

    @classmethod
    def get_scrapers(cls, name_list):
        enabled_scrapers = []
        for sub_class in cls.__subclasses__():
            if sub_class.__name__ in name_list:
                enabled_scrapers.append(sub_class)
        return enabled_scrapers


class TheBigPictures(BasePlugin):

    _title = 'The Boston Globe: The Big Picture'

    def _get_albums(self):
        self._albums = []
        url = 'https://www.bostonglobe.com/news/bigpicture'
        html = self._get_html(url)
        for _id, album in enumerate(parseDOM(html, 'section')):
            title = parseDOM(album, 'a')[0]
            album_url = 'https://www.bostonglobe.com' + parseDOM(album, 'a', ret='href')[0]
            d = parseDOM(album, 'div', attrs={'class': 'subhead geor'})[0]
            if not d:
                continue
            description = stripTags(self._parser.unescape(d))
            date = parseDOM(album, 'div', attrs={'class': 'pictureInfo-dateline geor'})[0]
            if date: description = date + "\n" + description
            pic = urllib2.quote(parseDOM(album, 'img', ret='src')[0])
            if not pic:
                continue
            self._albums.append({
                'title': title,
               'album_id': _id,
               'pic': 'http:' + pic,
               'description': description,
               'album_url': album_url
               })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        album_title = parseDOM(html, 'title')[0]
        images = parseDOM(html, 'div', attrs={'class': 'photo'})
        descs = parseDOM(html, 'article', attrs={'class': 'pcaption'})
        for _id, photo in enumerate(images):
            pic = urllib2.quote(parseDOM(photo, 'img', ret='src')[0])
            description = stripTags(self._parser.unescape(parseDOM(descs[_id], 'div', attrs={'class': 'gcaption geor'})[0]))
            self._photos[album_url].append({
                'title': '%d - %s' % (_id + 1, album_title),
               'album_title': album_title,
               'photo_id': _id,
               'pic': 'http:' + pic,
               'description': description,
               'album_url': album_url
               })

        return self._photos[album_url]

class AtlanticInFocus(BasePlugin):

    _title = 'The Atlantic: In Focus'

    def _get_albums(self):
        self._albums = []
        url = 'https://www.theatlantic.com/infocus/'
        html = self._get_html(url)
        pattern = r'@media\(min-width:\s*1632px\)\s*{\s*#river1 \.lead-image\s*{\s*background-image:\s*url\((.+?)\)'
        for _id, li in enumerate(parseDOM(html, 'li', attrs={'class': 'article'})):
            headline = parseDOM(li, 'h1')
            title = parseDOM( headline, 'a')[0]
            # add date to description:
            date = parseDOM( parseDOM(li, 'ul'), 'li')[1]
            match = re.search(pattern.replace('river1', 'river%d' % (_id + 1)), html)
            if match:
                self._albums.append({
                   'title': title,
                   'album_id': _id,
                   'pic': match.group(1),
                   'description': date + "\n" + stripTags(self._parser.unescape(parseDOM(li, 'p', attrs={'class': 'dek'})[0])),
                   'album_url': 'https://www.theatlantic.com' + parseDOM(headline, 'a', ret='href')[0]
                   })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        pattern = r'data-srcset=\"(.+?)\"'
        match_image = re.findall(pattern, html)
        album_title = self._parser.unescape(parseDOM(html, 'title')[0])
        for _id, p in enumerate(parseDOM(html, 'p', attrs={'class': 'caption'})):
            match_description = re.search('<span>(.+?)</span>', p)
            if match_description:
                self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                   'album_title': album_title,
                   'photo_id': _id,
                   'pic': match_image[_id * 5],
                   'description': stripTags(self._parser.unescape(match_description.group(1))),
                   'album_url': album_url
                   })

        return self._photos[album_url]


class TotallyCoolPix(BasePlugin):

    _title = 'TotallyCoolPix.com'

    def _get_albums(self):
        self._albums = []
        url = 'https://totallycoolpix.com'
        html = self._get_html(url)
        albums = parseDOM( html, 'div', {'class': 'item'} )
        for id, album in enumerate(albums):
            if not parseDOM( album, 'a', {'class': 'open'} ):
                continue
            title = parseDOM( album, 'h2' )[0]
            album_url = parseDOM( album, 'a', ret='href' )[0]
            p = parseDOM( album, 'p' )
            description = p[0].replace( '<br />', '' ) if p else ''
            # add date to description:
            description = stripTags( parseDOM( parseDOM( album, 'li' ), 'a')[0] ) + "\n" + description
            pic = parseDOM( album, 'img', ret='src' )[0]
            self._albums.append({
                'title': title,
                'album_id': id,
                'pic': pic,
                'description': description,
                'album_url': album_url}
            )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []

        html = self._get_html(album_url)
        for id, photo in enumerate( parseDOM( html, 'div', attrs={'class': 'image'}) ):
            img = parseDOM( photo, 'img', ret='src' )[0]
            if not img:
                continue
            if id == 0:
                album_title = parseDOM( photo, 'h2' )[0]
                # jump first entry as it is a repetition of the album description
                continue
                description = stripTags(self._parser.unescape(parseDOM( html, 'p', attrs={'class': 'desc'} )[0]))
            else:
                try:
                    description = self._parser.unescape(parseDOM( photo, 'p', {'class': 'info-txt'} )[0])
                except:
                    description = ''
            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'pic': img,
                'description': description,
                'album_url': album_url
            })
        if (id==0):
            # possibly a video:
            video = parseDOM( html, 'iframe', ret='src' )[0]
            self.log('possible video = ' + video)
            if re.match(r'.+youtube.com/.+', video):
                video_id = re.sub('.+/', '', video)
                self.log('youtube video = ' + video_id)
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.youtube/play/?video_id=' + video_id + ')')
            elif re.match(r'.+vimeo.com/.+', video):
                video_id = re.sub('.+/', '', video)
                self.log('vimeo video = ' + video_id)
                xbmc.executebuiltin('PlayMedia(plugin://plugin.video.vimeo/play/?video_id=' + video_id + ')')
            # if no match: previous processing have retrieved images
        return self._photos[album_url]


class NewYorkTimesLens(BasePlugin):

    _title = 'NewYorkTimes.com: Lens Blog'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://www.nytimes.com'
        url = home_url + '/section/lens'
        html = self._get_html(url)
        for id, album in enumerate( parseDOM( html, 'li', attrs={ 'class': 'css-[^"\']+' } ) ):
            title = parseDOM( album, 'h2' )
            if not title:
                continue

            album_url = parseDOM( album, 'a', ret='href' )[0]
            picture = parseDOM( album, 'img', ret='src' )[0]
            image = parseDOM( album, 'img', ret='srcSet' )[0]
            if re.search( r'Medium', image ):
                image = image.split(',')
                for picture in image:
                    if re.search( r'Medium', picture ):
                        picture = re.search( r'^[^\?]+', picture).group()
                        break
            description = parseDOM( album, 'p' )[0].encode('utf-8', 'ignore')
            date = re.search( r'/(20\d{2}/\d{2}/\d{2})/' ,  album_url )
            if ( date ):
                description = date.group(1).encode('utf-8', 'ignore') + "\n" + description
            self._albums.append({
               'title': stripTags( title[0] ),
               'album_id': id,
               'pic': picture,
               'description': description,
               'album_url': home_url + album_url
               })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []

        html = self._get_html(album_url)
        slide_html = parseDOM( html, 'figure', attrs={ 'class': '[^\'"]*?css-[^\'"]+' }, ret='item[IDid]{2}' )
        summaries = parseDOM( html, 'div', attrs={ 'class': '[^\'"]*?StoryBodyCompanionColumn[^\'"]*' } )
        for id, slide in enumerate( parseDOM( html, 'figure', attrs={ 'class': '[^\'"]*?css-[^\'"]+' } ) ):
            picture = slide_html[id]
            if not picture:
                continue
            description = ''
            for desc in enumerate( parseDOM( parseDOM( slide, 'figcaption' ), 'span', attrs={'class':'[^\'"]*'} ) ):
                description = description + "\n" + stripTags( desc[1].replace( '</span>', "\n" ) )
            title = parseDOM( parseDOM( html, 'h1' ), 'span' )[0]
            self.log( str( len(summaries)/len(slide_html) ) )
            self.log( str( (1 if len(summaries)/len(slide_html)<1 else int(len(summaries)/len(slide_html))) ) )
            try:
                summary = stripTags( u''.join( parseDOM( 
                        summaries[id*(1 if len(summaries)/len(slide_html)<1 else int(len(summaries)/len(slide_html)))+1], 
                            'p', attrs={'class': 'css-1ygdjhk e2kc3sl0'} ) ) )
            except:
                summary = ''
            self._photos[album_url].append({
               'title': title,
               'album_title': title,
               'photo_id': id,
               'pic': picture,
               'description': description[1:] + summary,
               'album_url': album_url
               })

        return self._photos[album_url]


class Reddit(BasePlugin):

    _title = 'Reddit'
    URL_PREFIX='https://www.reddit.com'

    def _get_albums(self):
        self._albums = []

        self._albums.append({
            'title': 'EarthPorn',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2sbq3/styles/communityIcon_0kgik2jq6y301.png',
            'description': 'Pictures of the earth',
            'album_url': self.URL_PREFIX + '/r/EarthPorn'}
        )
        self._albums.append({
            'title': 'SpacePorn',
            'album_id': 2,
            'pic': 'https://b.thumbs.redditmedia.com/GWtvw04-nxg-WqCltgj9ZWN5SzvHGjDf2sIvPpWKPes.png',
            'description': 'High Res Images of Space',
            'album_url': self.URL_PREFIX + '/r/SpacePorn'}
        )
        self._albums.append({
            'title': 'SeaPorn',
            'album_id': 3,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_0079D3.png',
            'description': 'Pictures of the sea',
            'album_url': self.URL_PREFIX + '/r/SeaPorn'}
        )
        self._albums.append({
            'title': 'BeachPorn',
            'album_id': 4,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_FF8717.png',
            'description': 'High-res images of Beaches from around the globe.',
            'album_url': self.URL_PREFIX + '/r/BeachPorn'}
        )
        self._albums.append({
            'title': 'AerialPorn',
            'album_id': 5,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_7193FF.png',
            'description': 'Pictures of the ground',
            'album_url': self.URL_PREFIX + '/r/AerialPorn'}
        )
        self._albums.append({
            'title': 'ExposurePorn',
            'album_id': 6,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_545452.png',
            'description': 'Long exposure photography',
            'album_url': self.URL_PREFIX + '/r/ExposurePorn'}
        )
        self._albums.append({
            'title': 'ViewPorn',
            'album_id': 7,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_46A508.png',
            'description': 'Rooms with a view',
            'album_url': self.URL_PREFIX + '/r/ViewPorn'}
        )
        self._albums.append({
            'title': 'AdrenalinePorn',
            'album_id': 8,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_EA0027.png',
            'description': 'Eye candy for extreme athletes and adrenaline junkies!',
            'album_url': self.URL_PREFIX + '/r/AdrenalinePorn'}
        )
        self._albums.append({
            'title': 'SummerPorn',
            'album_id': 9,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_FFB000.png',
            'description': 'Soaking in the sun',
            'album_url': self.URL_PREFIX + '/r/SummerPorn'}
        )
        self._albums.append({
            'title': 'CityPorn',
            'album_id': 10,
            'pic': 'https://b.thumbs.redditmedia.com/4KKF9mkNZECNka_ExAeyJlec1Vg6iz__kfujrBSEbuU.png',
            'description': 'Beautifuly cityscapes',
            'album_url': self.URL_PREFIX + '/r/CityPorn'}
        )
        self._albums.append({
            'title': 'WaterPorn',
            'album_id': 11,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_008985.png',
            'description': 'Waterscapes and aquatics',
            'album_url': self.URL_PREFIX + '/r/WaterPorn'}
        )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html( album_url )
        album_title = parseDOM( html, 'title' )[0]
        for id, photo in enumerate( parseDOM( html, 'div', attrs={'class': '_1poyrkZ7g36PawDueRza-J _11R7M_VOgKO1RJyRSRErT3'}) ):

            if ( XBMC_MODE and id%5==0 ):
                dialog = xbmcgui.Dialog()
                dialog.notification( 'Retrieving images: (' + str(id) + ')', 
                    'Please, wait ...', 
                    xbmcgui.NOTIFICATION_INFO, 8000 )

            try:
                description = parseDOM( photo, 'h2' )[0]
                description = replaceHTMLCodes( description.encode('utf-8', 'ignore') )
                img = parseDOM( parseDOM( photo, 'div', attrs={'class': '_3JgI-GOrkmyIeDeyzXdyUD'}), 'a', ret='href' )[0]
            except:
                self.log(' Upss ')
                continue

            if not img:
                self.log('no image or not a jpg')
                continue
            else:
                if img[0] != '/':
                    # only follow reddit images, not other 'promoted' posts:
                    continue
                img = self.URL_PREFIX + img
                pic = self._get_html( img )
                try:
                    pic = parseDOM( parseDOM( pic, 'div', attrs={'class': '_3Oa0THmZ3f5iZXAQ0hBJ0k'}), 'a', ret='href' )[0]
                    pic = replaceHTMLCodes ( pic ) # some '&amp;'' may be in urls
                except:
                    continue

            try:
                author = parseDOM( photo, 'a', {'class': '_2tbHP6ZydRpjI44J3syuqC s1461iz-1 gWXVVu'} )
                if author:
                    author = author[0].encode('utf-8', 'ignore')

                pic_time = parseDOM( photo, 'a', {'class': '_3jOxDPIQ0KaOWpzvSQo-1s'} )[0].encode('utf-8', 'ignore')
            except:
                author=''
                pic_time=''

            if author:
                description+="\n\n(Author: " + author + ")"
            if pic_time:
                description+="\n(@ " + pic_time + ")"

            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'author': author,
                'pic': pic,
                'description': description,
                'album_url': album_url,
            })

        return self._photos[album_url]


def get_scrapers(enabled_scrapers=None):
    if enabled_scrapers is None:
        enabled_scrapers = ALL_SCRAPERS
    scrapers = [
        scraper(i) for i, scraper
        in enumerate(BasePlugin.get_scrapers(enabled_scrapers))
    ]
    return scrapers
