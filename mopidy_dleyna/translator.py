from __future__ import absolute_import, unicode_literals

from mopidy import models

ALBUM_TYPE = 'container.album.musicAlbum'

ARTIST_TYPE = 'container.person.musicArtist'

_PATH_PREFIX = '/com/intel/dLeynaServer/server/'

_QUERYMAP = {
    'any': lambda caps: (
        ' or '.join(s + ' {0} "{1}"' for s in caps & {
            'DisplayName', 'Album', 'Artist', 'Genre', 'Creator'
        })
    ),
    'album': lambda caps: (
        'Album {0} "{1}"' if 'Album' in caps else None
    ),
    'artist': lambda caps: (
        ' or '.join(s + ' {0} "{1}"' for s in caps & {'Artist', 'Creator'})
    ),
    'date': lambda caps: (
        'Date = "{1}"' if 'Date' in caps else None  # TODO: inexact?
    ),
    'genre': lambda caps: (
        'Genre {0} "{1}"' if 'Genre' in caps else None
    ),
    'track_name': lambda caps: (
        ('DisplayName {0} "{1}" and Type = "music"'
         if 'DisplayName' in caps and 'Type' in caps else None)
    ),
    'track_no': lambda caps: (
        'TrackNumber = "{1}"' if 'TrackNumber' in caps else None
    )
}

# TODO: handle playlists and 'container.playlistContainer'
_REFMAP = {
    'audio': models.Ref.track,
    'container': models.Ref.directory,
    'container.genre.musicGenre': models.Ref.directory,
    'container.storageFolder': models.Ref.directory,
    'music': models.Ref.track,
    ALBUM_TYPE: models.Ref.album,
    ARTIST_TYPE: models.Ref.artist
}


def _quote(s):
    return unicode(s).replace('\\', '\\\\').replace('"', '\\"')


def _album(obj):
    try:
        name = obj['Album']
    except KeyError:
        return None
    else:
        return models.Album(name=name, uri=None)


def _artists(obj):
    artists = []
    for name in filter(None, obj.get('Artists', [obj.get('Creator')])):
        artists.append(models.Artist(name=name, uri=None))
    return artists


def ref(obj):
    type = obj.get('TypeEx', obj['Type'])
    try:
        return _REFMAP[type](name=obj['DisplayName'], uri=obj['URI'])
    except KeyError:
        raise ValueError('Object type "%s" not supported' % type)


def album(obj):
    return models.Album(
        artists=_artists(obj),
        name=obj['DisplayName'],
        num_tracks=obj.get('ItemCount', obj.get('ChildCount')),
        uri=obj['URI']
    )


def artist(obj):
    return models.Artist(name=obj['DisplayName'], uri=obj['URI'])


def track(obj):
    return models.Track(
        album=_album(obj),
        artists=_artists(obj),
        date=obj.get('Date'),
        genre=obj.get('Genre'),
        length=obj.get('Duration', 0) * 1000 or None,
        name=obj['DisplayName'],
        track_no=obj.get('TrackNumber'),
        uri=obj['URI']
    )


def model(obj):
    type = obj.get('TypeEx', obj['Type'])
    if type == 'music' or type == 'audio':
        return track(obj)
    elif type == ALBUM_TYPE:
        return album(obj)
    elif type == ARTIST_TYPE:
        return artist(obj)
    else:
        raise ValueError('Object type "%s" not supported' % type)


def images(obj):
    try:
        return [models.Image(uri=obj['AlbumArtURL'])]
    except KeyError:
        return []


def query(query, exact, searchcaps):
    terms = []
    caps = frozenset(searchcaps)
    op = '=' if exact else 'contains'
    for key, values in query.items():
        try:
            fmt = _QUERYMAP[key](caps)
        except KeyError:
            raise ValueError('Keyword "%s" not supported' % key)
        if fmt:
            terms.extend(fmt.format(op, _quote(value)) for value in values)
        else:
            raise ValueError('Keyword "%s" not supported by device' % key)
    return ('(%s)' % ') and ('.join(terms)) or '*'


def urifilter(fields):
    if 'URI' in fields:
        objfilter = fields[:]
        objfilter.remove('URI')
        objfilter.append('Path')
        objfilter.append('RefPath')
        return objfilter
    else:
        return fields


def urimapper(baseuri):
    def mapper(obj, index=len(_PATH_PREFIX)):
        objpath = obj.get('RefPath', obj['Path'])
        assert objpath.startswith(_PATH_PREFIX)
        _, sep, relpath = objpath[index:].partition('/')
        obj['URI'] = baseuri + sep + relpath
        return obj
    return mapper
