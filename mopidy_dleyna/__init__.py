import pathlib

import pkg_resources

from mopidy import config, exceptions, ext

__version__ = pkg_resources.get_distribution("Mopidy-dLeyna").version


class Extension(ext.Extension):

    dist_name = "Mopidy-dLeyna"
    ext_name = "dleyna"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        schema["upnp_browse_limit"] = config.Integer(minimum=0)
        schema["upnp_lookup_limit"] = config.Integer(minimum=0)
        schema["upnp_search_limit"] = config.Integer(minimum=0)
        schema["dbus_start_session"] = config.String()
        return schema

    def setup(self, registry):
        from .backend import dLeynaBackend

        registry.add("backend", dLeynaBackend)

    def validate_environment(self):
        try:
            import dbus  # noqa
        except ImportError:
            raise exceptions.ExtensionError("Cannot import dbus")
