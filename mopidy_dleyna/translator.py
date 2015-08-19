from __future__ import absolute_import, unicode_literals

from os.path import basename as basepath  # FIXME: server path?

from mopidy import models

from uritools import uriencode, urijoin

ALBUM_TYPE = 'container.album.musicAlbum'

ARTIST_TYPE = 'container.person.musicArtist'


def _quote(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def _album(baseuri, obj):
    if 'Album' not in obj:
        return None
    if 'Parent' in obj:
        baseuri += b'/' + basepath(obj['Parent'])
    name = obj['Album']
    images = [obj['AlbumArtURL']] if 'AlbumArtURL' in obj else None
    uri = baseuri + b'?' + uriencode('Album = ' + _quote(name))
    return models.Album(images=images, name=name, uri=uri)


def _artists(baseuri, obj):
    artists = []
    if 'Parent' in obj:
        baseuri += b'/' + basepath(obj['Parent'])
    for name in filter(None, obj.get('Artists', [obj.get('Creator')])):
        uri = baseuri + b'?' + uriencode('Artist = ' + _quote(name))
        artists.append(models.Artist(name=name, uri=uri))
    return artists


def ref(baseuri, obj):
    uri = urijoin(baseuri, basepath(obj.get('RefPath', obj['Path'])))
    name = obj['DisplayName']
    type = obj.get('TypeEx', obj['Type'])
    if type == 'music' or type == 'audio':
        return models.Ref.track(name=name, uri=uri)
    elif type == ALBUM_TYPE:
        return models.Ref.album(name=name, uri=uri)
    elif type == ARTIST_TYPE:
        return models.Ref.artist(name=name, uri=uri)
    elif type.startswith('container'):
        return models.Ref.directory(name=name, uri=uri)
    else:
        raise ValueError('Invalid DLNA model type: %s' % type)


def album(baseuri, obj):
    return models.Album(
        artists=_artists(baseuri, obj),
        name=obj['DisplayName'],
        num_tracks=obj.get('ItemCount', obj.get('ChildCount')),
        uri=urijoin(baseuri, basepath(obj.get('RefPath', obj['Path'])))
    )


def artist(baseuri, obj):
    return models.Artist(
        name=obj['DisplayName'],
        uri=urijoin(baseuri, basepath(obj.get('RefPath', obj['Path'])))
    )


def track(baseuri, obj):
    return models.Track(
        album=_album(baseuri, obj),
        artists=_artists(baseuri, obj),
        date=obj.get('Date'),
        genre=obj.get('Genre'),
        length=obj.get('Duration', 0) * 1000 or None,
        name=obj['DisplayName'],
        track_no=obj.get('TrackNumber'),
        uri=urijoin(baseuri, basepath(obj.get('RefPath', obj['Path'])))
    )


def model(baseuri, obj):
    type = obj.get('TypeEx', obj['Type'])
    if type == 'music' or type == 'audio':
        return track(baseuri, obj)
    elif type == ALBUM_TYPE:
        return album(baseuri, obj)
    elif type == ARTIST_TYPE:
        return artist(baseuri, obj)
    else:
        raise ValueError('Invalid DLNA model type: %s' % type)
