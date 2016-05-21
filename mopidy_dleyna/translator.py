from __future__ import absolute_import, unicode_literals

from mopidy import models

_QUERY = {
    'any': lambda caps: (
        ' or '.join(s + ' {0} "{1}"' for s in caps & {
            'DisplayName', 'Album', 'Artist', 'Genre'
        })
    ),
    'album': lambda caps: (
        'Album {0} "{1}"' if 'Album' in caps else None
    ),
    'albumartist': lambda caps: (
        'Artist {0} "{1}" and TypeEx = "container.album.musicAlbum"'
        if 'Artist' in caps and 'TypeEx' in caps
        else None
    ),
    'artist': lambda caps: (
        'Artist {0} "{1}"' if 'Artist' in caps else None
    ),
    'date': lambda caps: (
        'Date = "{1}"' if 'Date' in caps else None  # TODO: inexact?
    ),
    'genre': lambda caps: (
        'Genre {0} "{1}"' if 'Genre' in caps else None
    ),
    'track_name': lambda caps: (
        'DisplayName {0} "{1}" and Type = "music"'
        if 'DisplayName' in caps and 'Type' in caps
        else None
    ),
    'track_no': lambda caps: (
        'TrackNumber = "{1}"' if 'TrackNumber' in caps else None
    )
}

# TODO: handle playlists and 'container.playlistContainer'
_REFS = {
    'audio': models.Ref.track,
    'container': models.Ref.directory,
    'container.album': models.Ref.directory,
    'container.album.musicAlbum': models.Ref.album,
    'container.genre.musicGenre': models.Ref.directory,
    'container.person.musicArtist': models.Ref.artist,
    'container.storageFolder': models.Ref.directory,
    'music': models.Ref.track
}


def _album(obj):
    try:
        name = obj['Album']
    except KeyError:
        return None
    else:
        return models.Album(name=name, uri=None)


def _artists(obj):
    return (models.Artist(name=name) for name in obj.get('Artists', []))


def _quote(s):
    return unicode(s).replace('\\', '\\\\').replace('"', '\\"')


def ref(obj):
    type = obj.get('TypeEx', obj['Type'])
    try:
        translate = _REFS[type]
    except KeyError:
        raise ValueError('Object type "%s" not supported' % type)
    else:
        return translate(name=obj['DisplayName'], uri=obj['URI'])


def album(obj):
    return models.Album(
        uri=obj['URI'],
        name=obj['DisplayName'],
        artists=list(_artists(obj)),
        num_tracks=obj.get('ItemCount', obj.get('ChildCount')),
    )


def artist(obj):
    return models.Artist(name=obj['DisplayName'], uri=obj['URI'])


def track(obj):
    return models.Track(
        uri=obj['URI'],
        name=obj['DisplayName'],
        artists=list(_artists(obj)),
        album=_album(obj),
        genre=obj.get('Genre'),
        track_no=obj.get('TrackNumber'),
        date=obj.get('Date'),
        length=obj.get('Duration', 0) * 1000 or None,
        bitrate=obj.get('Bitrate', 0) * 8 or None
    )


def model(obj):
    type = obj.get('TypeEx', obj['Type'])
    if type == 'music' or type == 'audio':
        return track(obj)
    elif type == 'container.album.musicAlbum':
        return album(obj)
    elif type == 'container.person.musicArtist':
        return artist(obj)
    else:
        raise ValueError('Object type "%s" not supported' % type)


def images(obj):
    if 'AlbumArtURL' in obj:
        return obj['URI'], [models.Image(uri=obj['AlbumArtURL'])]
    else:
        return obj['URI'], []


def query(query, exact, searchcaps):
    op = '=' if exact else 'contains'
    terms = []
    for key, values in query.items():
        try:
            translate = _QUERY[key]
        except KeyError:
            raise NotImplementedError('Keyword "%s" not supported' % key)
        else:
            fmt = translate(frozenset(searchcaps))
        # TODO: fail at runtime/server? "any" handling?
        if fmt:
            terms.extend(fmt.format(op, _quote(value)) for value in values)
        else:
            raise NotImplementedError('Keyword "%s" not supported' % key)
    return ('(%s)' % ') and ('.join(terms)) or '*'
