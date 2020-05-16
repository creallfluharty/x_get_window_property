import struct
import array

import xcffib.xproto
import xcffib

from core import abstraction


class AtomGetter:
    def __init__(self, connection):
        self.connection = connection

    def by_name(self, name):
        atom_id = abstraction.get_atom_id_from_name(
            conn=self.connection,
            name=name,
        )

        atom = Atom(
            _id=atom_id,
            name=name,
        )
        return atom

    def by_id(self, _id):
        name = abstraction.get_atom_name_from_id(
            conn=self.connection,
            atom_id=_id,
        )

        atom = Atom(
            _id=_id,
            name=name,
        )
        return atom


class Atom:
    def __init__(self, _id, name):
        self.id = _id
        self.name = name


class Property:
    def __init__(self, value, property_type):
        self.value = value
        self.type = property_type


class WindowFactory:
    def __init__(self, connection, atom_getter, property_decoder):
        self.connection = connection
        self.atom_getter = atom_getter
        self.property_decoder = property_decoder

    def get_root(self):
        root_window_id = abstraction.get_root_window_id(self.connection)
        root_window = self.from_id(window_id=root_window_id)
        return root_window

    def from_id(self, window_id):
        window = Window(
            _id=window_id,
            connection=self.connection,
            atom_getter=self.atom_getter,
            property_decoder=self.property_decoder,
        )
        return window


class Window:
    def __init__(self, _id, connection, atom_getter, property_decoder):
        self.id = _id

        self._connection = connection
        self._atom_getter = atom_getter
        self._property_decoder = property_decoder

    def get_property(self, property_name):
        property_name_atom = self._atom_getter.by_name(property_name)

        buffer, type_atom_id, _format = abstraction.get_window_property(
            conn=self._connection,
            window_id=self.id,
            property_name_atom_id=property_name_atom.id,
        )
        type_atom = self._atom_getter.by_id(type_atom_id)
        _property = self._property_decoder.decode(
            buffer=buffer,
            type_name=type_atom.name,
            name=property_name_atom.name,
            _format=_format,
        )
        return _property


class WindowPropertyDecodeDelegator:
    def __init__(self, default_property_factory):
        self._type_to_window_property_factory_map = {}
        self._name_to_window_property_factory_map = {}

        self.default_property_factory = default_property_factory

    def register_by_type(self, type_name, window_property_factory, *, allow_overwrite=False):
        if type_name in self._type_to_window_property_factory_map and not allow_overwrite:
            raise ValueError()

        self._type_to_window_property_factory_map[type_name] = window_property_factory

    def register_by_name(self, name, window_property_factory, allow_overwrite=False):
        if name in self._name_to_window_property_factory_map and not allow_overwrite:
            raise ValueError()

        self._name_to_window_property_factory_map[name] = window_property_factory

    def decode(self, buffer, type_name, name, _format):
        property_factory = self._get_property_factory_for_property(type_name, name)

        window_property = property_factory(
            buffer=buffer,
            type_name=type_name,
            name=name,
            _format=_format,
        )
        return window_property

    def _get_property_factory_for_property(self, type_name, name):
        if name in self._name_to_window_property_factory_map:
            factory = self._name_to_window_property_factory_map[name]
        elif type_name in self._type_to_window_property_factory_map:
            factory = self._type_to_window_property_factory_map[type_name]
        else:
            factory = self.default_property_factory

        return factory


class FormatListFactory:
    def __init__(self):
        self._integer_types = 'BHIL'
        self._size_to_struct_code_map = self._get_size_to_struct_code_map(self._integer_types)

    def _get_size(self, struct_code):
        return struct.calcsize(struct_code)

    def _get_size_to_struct_code_map(self, codes):
        size_to_struct_code_map = {
            self._get_size(code): code
            for code in codes
        }
        return size_to_struct_code_map

    def __call__(self, buffer, type_name, name, _format):
        item_size = _format // 8
        struct_code = self._size_to_struct_code_map[item_size]
        format_list = array.array(struct_code, buffer)
        return format_list


class FromIDListConverter:
    def __init__(self, from_id_factory, format_list_factory):
        self._from_id_factory = from_id_factory
        self._format_list_factory = format_list_factory

    def __call__(self, buffer, type_name, name, _format):
        id_list = self._format_list_factory(
            buffer=buffer,
            type_name=type_name,
            name=name,
            _format=_format,
        )

        objects = [self._from_id_factory(_id) for _id in id_list]
        return objects


def main():
    conn = xcffib.connect()

    atom_getter = AtomGetter(conn)

    format_list_factory = FormatListFactory()
    window_property_decoder = WindowPropertyDecodeDelegator(default_property_factory=format_list_factory)

    window_factory = WindowFactory(connection=conn, atom_getter=atom_getter, property_decoder=window_property_decoder)

    window_list_property_decoder = FromIDListConverter(window_factory.from_id, format_list_factory)
    window_property_decoder.register_by_type('WINDOW', window_list_property_decoder)

    def utf8_string_decoder(buffer, type_name, name, _format):
        return buffer.decode()

    window_property_decoder.register_by_type('UTF8_STRING', utf8_string_decoder)
    window_property_decoder.register_by_type('STRING', utf8_string_decoder)

    root = window_factory.get_root()

    client_list = root.get_property('_NET_CLIENT_LIST')

    for client in client_list:
        print(client.get_property('_NET_WM_NAME'))


if __name__ == '__main__':
    main()
