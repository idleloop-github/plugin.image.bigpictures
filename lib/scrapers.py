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
#    Modified by idleloop@yahoo.com: 2017, 2018, 2019, 2021
#

import re
import urllib2
import time
from random import randint
import HTMLParser # HTMLParser().unescape()

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
    'AtlanticInFocus',
    'TimePhotography',
    'ReadingthePictures',
    'Reddit',
    'TotallyCoolPix',
    'NewYorkTimesLens',
)


class BasePlugin(object):

    _title = ''
    _id = 0

    def __init__(self, _id):
        self._albums = []
        self._photos = {}
        self._id = _id
        self._parser = HTMLParser.HTMLParser()

    # https://stackoverflow.com/questions/44927922/replace-all-unicode-codes-with-characters-in-python
    unicode_escape = re.compile( r'\\u00([a-fA-F0-9]{2})' )
    def replace_unicode_codes(self, m):
        return ''.join(m.groups('')).decode("hex")

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


class AtlanticInFocus(BasePlugin):

    _title = 'The Atlantic: In Focus'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://www.theatlantic.com'
        url = home_url + '/photo/'
        html = self._get_html(url)

        css = parseDOM( html, 'style', attrs={ 'type': 'text/css' } )[0]
        pictures = re.finditer( r'#river(?P<river>[0-9]+) \.lead-image.?\{.{1,10}background-image: url\("(?P<url>.+?/.+?x(?P<height>[0-9]+)[^"]+)"', css, re.DOTALL )

        containers  = parseDOM( html, 'div', attrs={ 'id': 'home-hero' } )  # header container
        containers += parseDOM( html, 'li',  attrs={ 'class': 'article' } ) # <li> containers
        for _id, li in enumerate( containers ):
            # this is the header container (<div id="home-hero">)
            title = parseDOM( li, 'h1' )[0]
            try:
                # this is one of the <li id="river#"> containers
                title = parseDOM( title, 'a' )[0]
            except Exception:
                pass
            # add date to description:
            try:
                date = parseDOM( parseDOM(li, 'ul'), 'li', attrs={'class': 'date'} )[0]
            except Exception:
                date = ''
            try:
                # this is the header container (<div id="home-hero">)
                picture = parseDOM( li, 'img', ret='src' )[0]
            except Exception:
                # this is one of the <li id="river#"> containers
                resolution = 0
                for picture_line in pictures:
                    self.log(picture_line)
                    if picture_line.group('river') == str(_id):
                        # take the last available resolution, which is the greater one (hopefully)
                        if resolution < picture_line.group('height'):
                            picture = picture_line.group('url')
                            resolution = picture_line.group('height')
            try:
                description = parseDOM(li, 'p', attrs={'class': 'dek'})[0]
            except Exception:
                # description (<p></p>) may not exists:
                description = title
            self._albums.append({
                'title': self._parser.unescape( title ),
                'album_id': _id,
                'pic': picture,
                'description': date + "\n" + stripTags( self._parser.unescape( description ) ),
                'album_url': home_url + parseDOM(li, 'a', ret='href')[0]
                })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        pattern = r'source data-srcset=\"(.+?)\"'
        match_image = re.findall(pattern, html)
        album_title = self._parser.unescape(parseDOM(html, 'title')[0])
        for _id, p in enumerate(parseDOM(html, 'p', attrs={'class': 'caption'})):
            match_description = re.search('<span>(.+?)</span>', p)
            if match_description:
                self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                   'album_title': self._parser.unescape( album_title ),
                   'photo_id': _id,
                   'pic': match_image[_id * 5],
                   'description': stripTags(self._parser.unescape(match_description.group(1))),
                   'album_url': album_url
                   })

        return self._photos[album_url]


class TimePhotography(BasePlugin):

    _title = 'Time - Photography'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://time.com'
        url = home_url + '/tag/photography/'
        html = self._get_html(url)

        articles  = parseDOM( html, 'article' )
        for _id, article in enumerate( articles ):
            title = parseDOM( article, 'a' )[1]
            picture = parseDOM( article, 'div', ret='data-src' )[0]
            description = parseDOM(article, 'div', attrs={'class': 'summary margin-8-bottom desktop-only'})[0]
            self._albums.append({
                'title': self._parser.unescape( title ),
                'album_id': _id,
                'pic': picture,
                'description': stripTags( self._parser.unescape( description ) ),
                'album_url': home_url + parseDOM(article, 'a', ret='href')[0]
                })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        album_title = re.findall( r'"headline":"(?P<title>[^"]+)"', html )[0]
        images  = parseDOM( html, 'div', attrs={'class': 'component lazy-image lead-media marquee_large_2x.*'}, ret='data-src' )
        images += parseDOM( parseDOM( html, 'div', attrs={'class': 'image-wrapper'}), 'div', attrs={'class': 'component lazy-image.*'}, ret='data-src' )
        if len(images) == 0:
            # if there are no images that's because the article contains just a video: so show its poster only
            images = [ parseDOM( html, 'video', ret='poster' )[0] ]
            self.log( list(images) )
            descriptions = [ '' ]
        else:
            descriptions  = parseDOM( html, 'div', attrs={'class': 'component lazy-image lead-media marquee_large_2x.*'}, ret='data-alt' )
            descriptions += parseDOM( parseDOM( html, 'div', attrs={'class': 'image-wrapper'}), 'div', attrs={'class': 'component lazy-image.*'}, ret='data-alt' )
        for _id, image in enumerate( images ):
            self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                'album_title': self._parser.unescape( album_title ),
                'photo_id': _id,
                'pic': image,
                'description': stripTags( self._parser.unescape( descriptions[_id] ) ),
                'album_url': album_url
                })

        return self._photos[album_url]


class ReadingthePictures(BasePlugin):

    _title = 'Reading the Pictures .org'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://www.readingthepictures.org'
        url = home_url + '/category/notes/'
        html = self._get_html(url)

        articles  = parseDOM( html, 'div', attrs={'class': 'article'} )
        for _id, article in enumerate( articles ):
            title = parseDOM( article, 'a', ret='title' )[0]
            picture = parseDOM( article, 'img', ret='src' )[0]
            description = parseDOM( article, 'p' )[0]
            self._albums.append({
                'title': self._parser.unescape( title ),
                'album_id': _id,
                'pic': picture,
                'description': stripTags( self._parser.unescape( description ) ),
                'album_url': parseDOM(article, 'a', ret='href')[0]
                })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        album_title = parseDOM( html, 'meta', attrs={'property': 'og:title'}, ret='content' )[0]
        alternative_distribution = 0
        images = parseDOM( html, 'div', attrs={'class': 'wp-caption alignnone'} )
        if len(images) > 0:
            # may be alternative div classes are used:          
            alternative_distribution = 1
        else:
            images  = parseDOM( html, 'section', attrs={'class': 'single-intro wysiwyg'} )
            images += parseDOM( html, 'section', attrs={'class': 'single-large-photo'} )
        for _id, image in enumerate( images ):
            try:
                if alternative_distribution == 0:
                    try:
                        description = parseDOM( image, 'div', attrs={'class': 'caption'} )[0] # description for first image
                    except Exception:
                        description = parseDOM( image, 'figcaption' )[0] # description for images after the first one
                else:
                    description = parseDOM( image, 'p', attrs={ 'class': 'wp-caption-text' })[0]
                # clean description:
                try:
                    description = stripTags( description ).replace( '&nbsp;', '' ).replace( chr(9), '' )
                    description_items = re.search( r'^(?P<author>.+)Caption: *(?P<caption>.+)', description, re.DOTALL )
                    description = re.sub( r'\n+', '', description_items.group('caption') ) + "\n\n" + \
                                    description_items.group('author')
                except Exception:
                    description = ''
                picture = parseDOM( image, 'img', ret='src' )[0]
                if alternative_distribution == 1:
                    picture = re.search( r'(?P<pic>https://[^ ]+) [^ ]+?$', parseDOM( image, 'img', ret='srcset' )[0] ).group('pic')
                self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                    'album_title': self._parser.unescape( album_title ),
                    'photo_id': _id,
                    'pic': picture,
                    'description': self._parser.unescape( description ),
                    'album_url': album_url
                    })
            except Exception:
                continue

        if len( self._photos[album_url] ) == 0:
            self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                'album_title': album_title,
                'photo_id': _id,
                'pic': 'https://www.readingthepictures.org/wp-content/uploads/2019/04/1_LAT_Mueller.jpg',
                'description': 'no more images here !',
                'album_url': album_url
                })
            if XBMC_MODE:
                dialog = xbmcgui.Dialog()
                dialog.notification( 'Reading the Pictures .org :',
                    'no more images here !',
                    xbmcgui.NOTIFICATION_INFO, int(2000) )

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
            'pic': 'https://styles.redditmedia.com/t5_2sbq3/styles/communityIcon_63gyqtn0h9v41.png',
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

        if XBMC_MODE:
            dialog = xbmcgui.Dialog()
            dialog.notification( 'The Big Picture',
                'retrieving reddit images ...',
                xbmcgui.NOTIFICATION_INFO, int(2000) )

        html = self._get_html( album_url )
        album_title = parseDOM( html, 'title' )[0].decode('utf-8', 'ignore')
        json_data = parseDOM( html, 'script', attrs={'id': 'data'} )[0].encode('utf-8', 'ignore')
        # try to replace some unicode codes of type \u00xy :
        json_data = self.unicode_escape.sub( self.replace_unicode_codes, json_data )
        # there may be no "content" tag in "models" array, so it'll be extracted later:
        json_regex = r'"(?P<id>[^"]+)":{"id":"(?P=id)".+?"title":"(?P<title>[^"]+)","author":"(?P<author>[^"]+)".+?"domain":"(?P<domain>[^"]+)".+?"isSponsored":(?P<sponsored>[^,]+),(?P<data>.+?)"created":(?P<pic_time>\d+),'
        for image_data in re.finditer( json_regex, json_data ):
            domain = image_data.group('domain')
            if ( domain == 'reddit.com' or domain.startswith('self.') ):
                continue
            author = image_data.group('author')
            # remove registers with adverstisments
            if image_data.group('sponsored') == 'true':
                continue
            secoundary_regex = r'("content":"(?P<pic>[^"]+)"),(?P<urls>.+?)'
            secoundary_data = re.search( secoundary_regex, image_data.group('data') )
            try:
                pic = secoundary_data.group('pic')
            except:
                continue
            try:
                if ( 'external-preview.redd.it' not in pic and 'i.redd.it' not in pic ):
                    pic = re.search( r'(https://external-preview.redd.it/[^"]+)', secoundary_data.group('urls') )
                    if pic:
                        pic = pic.group(0)
                    else:
                        continue
            except:
                continue
            pic = pic.replace( '\u0026', '&' )
            pic_time = image_data.group('pic_time')
            # convert Unix time to UTC:
            pic_time = time.strftime( "%Y-%m-%d %H:%M", time.localtime( int( int( pic_time ) / 1000 ) ) )

            description = image_data.group('title').decode('utf-8', 'ignore').replace( '\\' , '' )
            description+= "\n\nAuthor: " + author
            description+= "  @ " + pic_time

            self._photos[album_url].append({
                'title': album_title,
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
