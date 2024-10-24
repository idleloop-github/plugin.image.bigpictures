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
#    Modified by idleloop@yahoo.com: 2017, 2018, 2019, 2021, 2023
#

import re
import urllib2
from urllib import quote
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
    'BBCNews',
    'PhotojournalismNow',
    'CNNPhotos',
    'Reddit',
)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0'

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
        url = url.encode('utf-8', 'ignore')
        self.log('_get_html opening url "%s"' % url)
        url_match = re.match( r'(.+)/([^/]+)/$', url )
        if ( url_match ):
            url = url_match.group(1) + '/' + quote( url_match.group(2) ) + '/'
        req = urllib2.Request( url , None, { 'User-Agent' : USER_AGENT })
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
        pictures = re.findall( r'#river(?P<river>[0-9]+) \.lead-image.?\{.{1,10}background-image: url\("(?P<url>.+?/.+?x(?P<height>[0-9]+)[^"]+)"', css, re.DOTALL )

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
                    if picture_line[0] == str(_id):
                        # take the greater resolution
                        if resolution < int(picture_line[2]):
                            picture = picture_line[1]
                            resolution = int(picture_line[2])
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
                   'album_title': album_title,
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

        articles = parseDOM( html, 'div', attrs={'class': 'taxonomy-tout *'} )
        for _id, article in enumerate( articles ):
            title = parseDOM( article, 'h2' )[0]
            picture = parseDOM( article, 'img', ret='src' )[0]
            album_url = home_url + parseDOM(article, 'a', ret='href')[0]
            try:
                description = parseDOM(article, 'h3')[0]
            except Exception:
                description = ''
            self._albums.append({
                'title': self._parser.unescape( title ),
                'album_id': _id,
                'pic': picture,
                'description': stripTags( self._parser.unescape( description ) ),
                'album_url': album_url
                })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        album_title = self._parser.unescape( re.findall( r'"headline":"(?P<title>[^"]+)"', html )[0] )
        images = parseDOM( html, 'figure' )
        if len(images) == 0:
            images = [ '' ]
            descriptions = [ '' ]
        for _id, image in enumerate( images ):
            try:
                image_url = parseDOM( image, 'img', attrs={}, ret='src' )[0]
            except Exception:
                continue
            try:
                description  = parseDOM( image, 'span' )[0]
            except Exception:
                description = ''
            self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                'album_title': album_title,
                'photo_id': _id,
                'pic': image_url,
                'description': stripTags( self._parser.unescape( description ) ),
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
        album_title = self._parser.unescape( parseDOM( html, 'meta', attrs={'property': 'og:title'}, ret='content' )[0] )
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
                    'album_title': album_title,
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


class BBCNews(BasePlugin):

    _title = 'BBC News In Pictures'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://www.bbc.com'
        url = home_url + '/news/in_pictures'
        html = self._get_html(url)
        html = html.replace( 'srcSet', 'srcset' )

        section = parseDOM( html, 'section', attrs={'data-analytics_group_name': ''} )[0]
        articles = parseDOM( section, 'div', attrs={'data-testid': '[^"]+-card'})
        section = parseDOM( html, 'section', attrs={'data-analytics_group_name': 'Features'} )[0]
        articles.extend( parseDOM( section, 'div', attrs={'data-testid': '[^"]+-card'}) )
        section = parseDOM( html, 'section', attrs={'data-analytics_group_name': 'Week in pictures'} )[0]
        articles.extend( parseDOM( section, 'div', attrs={'data-testid': '[^"]+-card'}) )
        section = parseDOM( html, 'section', attrs={'data-analytics_group_name': 'Your pictures'} )[0]
        articles.extend( parseDOM( section, 'div', attrs={'data-testid': '[^"]+-card'}) )
        for _id, article in enumerate( articles ):
            title = stripTags( parseDOM( article, 'h2' )[0] )
            picture = 'https://www.bbc.com/bbcx/apple-touch-icon.png'
            description = ''
            try:
                picture = parseDOM( article, 'img', ret='srcset')[0]
                picture = re.search( r', *(?P<bigger_url>https://[^ ]+) \d+w$', picture ).group('bigger_url')
                description = parseDOM( article, 'img', ret='alt')[0]
            except Exception:
                pass
            description = parseDOM( article, 'p' )[0] + ((' | ' + description) if (description != '') else '')
            try:
                timestamp = parseDOM( article, 'span' )[0] + ' | ' + parseDOM( article, 'span' )[1]
            except Exception:
                pass
            self._albums.append({
                'title': self._parser.unescape( title ),
                'album_id': _id,
                'pic': picture,
                'description': stripTags( self._parser.unescape( description + "\n\nPosted " + timestamp ) ),
                'album_url': home_url + parseDOM(article, 'a', ret='href')[0]
                })

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []
        html = self._get_html(album_url)
        html = html.replace( 'srcSet', 'srcset' )
        album_title = stripTags( self._parser.unescape( parseDOM( html, 'h1' )[0] ) )
        pictures = parseDOM( html, 'div', attrs={'data-testid': 'image'} )
        pictures = parseDOM( ''.join(pictures), 'img', ret='srcset' )
        descriptions = parseDOM( html, 'figcaption' )
        if ( len(descriptions) == 0 ):
            descriptions = [''] * len(pictures)
        id_picture = 0
        for _id, description in enumerate( descriptions ):
            try:
                description = stripTags( self._parser.unescape( description ) ).\
                                replace( 'image caption','' )
                condition = True
                while ( condition ):
                    picture = pictures[id_picture]
                    picture = re.search( r', *(?P<bigger_url>https://[^ ]+) \d+w$', picture ).group('bigger_url')
                    id_picture += 1
                    if ( re.search( r'(transparent|line)[^\."]+\.png', picture ) == None ):
                        condition = False
                if ( description == '' and re.search( r'banner[^\."]+\.png', picture ) != None ):
                    continue
                self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                    'album_title': album_title,
                    'photo_id': _id,
                    'pic': picture,
                    'description': self._parser.unescape( description ),
                    'album_url': album_url
                    })
            except Exception:
                continue

        return self._photos[album_url]


class PhotojournalismNow(BasePlugin):

    _title = 'Photojournalism Now'

    def _get_albums(self):
        self._albums = []
        home_url = 'https://photojournalismnow43738385.wordpress.com'
        url = home_url + '/'
        html = self._get_html(url)

        articles  = parseDOM( html, 'article' )
        for _id, article in enumerate( articles ):
            title = parseDOM( parseDOM( article, 'h1' )[0], 'a')[0]
            picture = parseDOM( article, 'img', ret='src' )[0]
            picture = re.search( r'^([^\?]+)', picture ).group(1)
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
        album_title = self._parser.unescape( parseDOM( html, 'title' )[0] )
        pictures = parseDOM( html, 'figure' )
        for _id, picture in enumerate( pictures ):
                try:
                    image = parseDOM( picture, 'img', ret='srcset' )[0]
                    image_resolutions = re.findall( r'(?P<url>https://[^ ]+) (?P<resolution>\d+)w', image )
                    resolution = 0
                    for image_line in image_resolutions:
                        # take the greater resolution
                        if resolution < int(image_line[1]):
                            image = image_line[0]
                            resolution = int(image_line[1])
                    try:
                        description = parseDOM( picture, 'figcaption' )[0]
                    except Exception:
                        description = ''
                    self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                        'album_title': album_title,
                        'photo_id': _id,
                        'pic': image,
                        'description': stripTags( self._parser.unescape( description ) ),
                        'album_url': album_url
                        })
                except Exception:
                    continue

        return self._photos[album_url]


class CNNPhotos(BasePlugin):

    _title = 'CNN Photos'

    def _get_albums(self):
        self._albums = []

        if XBMC_MODE:
            dialog = xbmcgui.Dialog()
            dialog.notification( 'The Big Picture',
                'retrieving CNN photos ...',
                xbmcgui.NOTIFICATION_INFO, int(5000) )

        home_url = 'https://edition.cnn.com/'
        url = home_url + 'world/photos/'
        html = self._get_html(url)
        html = parseDOM( html, 'section', attrs={'class': 'layout__wrapper layout-no-rail__wrapper'} )[0]

        articles  = parseDOM( html, 'div', attrs={'class': r'[\w\d\-\_\. ]+container__item[\w\d\-\_\. ]+'} )
        for _id, article in enumerate( articles ):
            try:
                title = stripTags( parseDOM( article, 'div', attrs={'class': 'container__text.+'} )[0] )
                picture = re.sub( '\?.+', '', parseDOM( article, 'img', ret='src' )[0] )
                description = parseDOM( article, 'span', attrs={'data-editable': 'headline'} )[0]
                album_url = parseDOM(article, 'a', ret='href')[0]
                if ( re.match( r'^/', album_url ) ):
                    album_url = home_url + album_url
                self._albums.append({
                    'title': self._parser.unescape( title ),
                    'album_id': _id,
                    'pic': picture,
                    'description': stripTags( self._parser.unescape( description ) ),
                    'album_url': album_url
                    })
            except Exception:
                continue

        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []

        if XBMC_MODE:
            dialog = xbmcgui.Dialog()
            dialog.notification( 'The Big Picture',
                'retrieving CNN photos ...',
                xbmcgui.NOTIFICATION_INFO, int(5000) )

        html = self._get_html(album_url)
        album_title = self._parser.unescape( parseDOM( html, 'title' )[0] )
        figures = parseDOM( html, 'figure' )
        if ( len(figures) == 0 ):
            pictures = parseDOM( html, 'picture' )
        else:
            pictures = figures
            figures = []
        descriptions = parseDOM( html, 'span', attrs={'data-editable': 'metaCaption'} )
        if ( len(descriptions) == 0 ):
            descriptions = parseDOM( html, 'figcaption' )
        for _id, picture in enumerate( pictures ):
            try:
                image = parseDOM( picture, 'img', ret='src' )[0]
                if ( re.match( '^data:image', image ) ):
                    image = parseDOM( picture, 'img', ret='data-src' )[0]
                if ( image[0] == '.' ):
                    image = album_url + image[2:]
                elif ( not re.match( r'^http', image) ):
                        image = album_url + image
                description = descriptions[_id]
                self._photos[album_url].append({'title': '%d - %s' % (_id + 1, album_title),
                    'album_title': album_title,
                    'photo_id': _id,
                    'pic': image,
                    'description': stripTags( self._parser.unescape( description ) ),
                    'album_url': album_url
                    })
            except Exception:
                continue

        return self._photos[album_url]


class Reddit(BasePlugin):

    _title = 'Reddit'
    URL_PREFIX='https://www.reddit.com'

    def _get_albums(self):
        self._albums = []

        self._albums.append({
            'title': 'EarthPorn',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2sbq3/styles/communityIcon_pf6xg83rv3981.png',
            'description': 'Pictures of the earth',
            'album_url': self.URL_PREFIX + '/r/EarthPorn'}
        )
        self._albums.append({
            'title': 'SpacePorn',
            'album_id': 2,
            'pic': 'https://b.thumbs.redditmedia.com/GWtvw04-nxg-WqCltgj9ZWN5SzvHGjDf2sIvPpWKPes.png',
            'description': 'High Res Images of Space',
            'album_url': self.URL_PREFIX + '/r/spaceporn'}
        )
        self._albums.append({
            'title': 'SeaPorn',
            'album_id': 3,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_0079D3.png',
            'description': 'Pictures of the sea',
            'album_url': self.URL_PREFIX + '/r/seaporn'}
        )
        self._albums.append({
            'title': 'BeachPorn',
            'album_id': 4,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_FF8717.png',
            'description': 'High-res images of Beaches from around the globe.',
            'album_url': self.URL_PREFIX + '/r/beachporn'}
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
            'album_url': self.URL_PREFIX + '/r/waterporn'}
        )
        self._albums.append({
            'title': 'lomography',
            'album_id': 1,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_0079D3.png',
            'description': 'Lomography',
            'album_url': self.URL_PREFIX + '/r/lomography'}
        )
        self._albums.append({
            'title': 'filmphotography',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2re71/styles/communityIcon_jyuj6v194vva1.png',
            'description': 'Film photography',
            'album_url': self.URL_PREFIX + '/r/filmphotography'}
        )
        self._albums.append({
            'title': 'analog',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2r344/styles/communityIcon_arrf56nbq1t81.png',
            'description': 'Analog',
            'album_url': self.URL_PREFIX + '/r/analog'}
        )
        self._albums.append({
            'title': 'HDR',
            'album_id': 1,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_0079D3.png',
            'description': 'HDR',
            'album_url': self.URL_PREFIX + '/r/HDR'}
        )
        self._albums.append({
            'title': 'portraits',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2sxa6/styles/communityIcon_ufzy3czufc871.png',
            'description': 'Portraits',
            'album_url': self.URL_PREFIX + '/r/portraits'}
        )
        self._albums.append({
            'title': 'portraitphotos',
            'album_id': 1,
            'pic': 'https://www.redditstatic.com/avatars/avatar_default_02_0079D3.png',
            'description': 'Portrait photos',
            'album_url': self.URL_PREFIX + '/r/portraitphotos'}
        )
        self._albums.append({
            'title': 'pics',
            'album_id': 1,
            'pic': 'https://b.thumbs.redditmedia.com/VZX_KQLnI1DPhlEZ07bIcLzwR1Win808RIt7zm49VIQ.png',
            'description': 'Pics',
            'album_url': self.URL_PREFIX + '/r/pics'}
        )
        self._albums.append({
            'title': 'fashionphotography',
            'album_id': 1,
            'pic': 'https://styles.redditmedia.com/t5_2req6/styles/communityIcon_ew9kdggkk1641.jpg',
            'description': 'Fashion photography',
            'album_url': self.URL_PREFIX + '/r/fashionphotography'}
        )
        return self._albums

    def _get_photos(self, album_url):
        self._photos[album_url] = []

        if XBMC_MODE:
            dialog = xbmcgui.Dialog()
            dialog.notification( 'The Big Picture',
                'retrieving reddit images ...',
                xbmcgui.NOTIFICATION_INFO, int(10000) )

        html = self._get_html( album_url )

        album_title = parseDOM( html, 'shreddit-title', ret='title' )[0].decode('utf-8', 'ignore')
        # now more publications must be retrieved, so the feed must be located and retouched:
        feed = self.URL_PREFIX + parseDOM( html, 'faceplate-partial', attrs={'method': 'GET'}, ret='src' )[0]
        feed = feed.replace( '&amp;', '&' )
        # retouched to retrieve 25 images:
        feed = re.sub( r'feedLength=\d+', 'feedLength=25', feed )
        html = self._get_html( feed )
        shreddit_post = parseDOM( html, 'shreddit-post')
        description_post = parseDOM( html, 'shreddit-post', ret='post-title')
        author_post = parseDOM( html, 'shreddit-post', ret='author')
        id = 0
        for _id, image_data in enumerate( shreddit_post ):
            try:
                pic_time = parseDOM( image_data, 'faceplate-timeago', ret='ts' )[0]

                description = description_post[_id]
                description+= "\n\nAuthor: " + author_post[_id]
                description+= "  @ " + pic_time

                pic = parseDOM( image_data, 'img', attrs={'class': 'i18n-post-media-img media-lightbox-img'}, ret='src' )[0]

                if ( XBMC_MODE and id > 0 and id % 5 == 0 ):
                    dialog = xbmcgui.Dialog()
                    dialog.notification( 'The Big Picture',
                        str(id) + ' reddit images so far...',
                        xbmcgui.NOTIFICATION_INFO, int(5000) )
            except Exception:
                continue

            self._photos[album_url].append({
                'title': '%d - %s' % (id + 1, album_title),
                'album_title': album_title,
                'photo_id': id,
                'author': author_post[_id],
                'pic': pic,
                'description': stripTags( self._parser.unescape( description ) ),
                'album_url': album_url,
            })

            id += 1

        return self._photos[album_url]


def get_scrapers(enabled_scrapers=None):
    if enabled_scrapers is None:
        enabled_scrapers = ALL_SCRAPERS
    scrapers = [
        scraper(i) for i, scraper
        in enumerate(BasePlugin.get_scrapers(enabled_scrapers))
    ]
    return scrapers
