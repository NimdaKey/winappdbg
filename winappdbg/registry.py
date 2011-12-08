#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2011, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import with_statement

"""
Registry module.

@group Instrumentation:
    Registry, RegistryKey
"""

__revision__ = "$Id$"

__all__ = ['Registry']

import win32
import collections
import warnings

try:
    from psyco.classes import *
except ImportError:
    pass

#==============================================================================

class _RegistryContainer (object):
    """
    Base class for L{Registry} and L{RegistryKey}.
    """

    # Dummy object to detect empty arguments.
    class __EmptyArgument:
        pass
    __emptyArgument = __EmptyArgument()

    def __init__(self):
        self.__default = None

    def has_key(self, name):
        return name in self

    def get(self, name, default=__emptyArgument):
        try:
            return self[name]
        except KeyError:
            if default is RegistryKey.__emptyArgument:
                return self.__default
            return default

    def setdefault(self, default):
        self.__default = default

    def __iter__(self):
        return self.iterkeys()

#==============================================================================

class RegistryKey (_RegistryContainer):
    """
    Exposes a single Windows Registry key as a dictionary-like object.
    
    @see: L{Registry}
    
    @type path: str
    @ivar path: Registry key path.
    
    @type handle: L{win32.RegistryKeyHandle}
    @ivar handle: Registry key handle.
    """

    def __init__(self, path, handle):
        """
        @type  path: str
        @param path: Registry key path.
        
        @type  handle: L{win32.RegistryKeyHandle}
        @param handle: Registry key handle.
        """
        super(RegistryKey, self).__init__()
        if path.endswith('\\'):
            path = path[:-1]
        self._path   = path
        self._handle = handle

    @property
    def path(self):
        return self._path

    @property
    def handle(self):
        return self._handle

    def __contains__(self, name):
        try:
            win32.RegQueryValueEx(self._handle, name, False)
            return True
        except WindowsError:
            if win32.winerror(e) == win32.ERROR_FILE_NOT_FOUND:
                return False
            raise

    def __getitem__(self, name):
        try:
            return win32.RegQueryValueEx(self._handle, name)[0]
        except WindowsError, e:
            if win32.winerror(e) == win32.ERROR_FILE_NOT_FOUND:
                raise KeyError(name)
            raise

    def __setitem__(self, name, value):
        win32.RegSetValueEx(self._handle, name, value)

    def __delitem__(self, name):
        win32.RegDeleteValue(self._handle, name)

    def iterkeys(self):
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index, False)
            if resp is None:
                break
            yield resp[0]
            index += 1

    def itervalues(self):
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index)
            if resp is None:
                break
            yield resp[2]
            index += 1

    def iteritems(self):
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index)
            if resp is None:
                break
            yield resp[0], resp[2]
            index += 1

    def keys(self):
        # return list(self.iterkeys())   # that can't be optimized by psyco
        keys = list()
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index, False)
            if resp is None:
                break
            keys.append(resp[0])
            index += 1
        return keys

    def values(self):
        # return list(self.itervalues()) # that can't be optimized by psyco
        values = list()
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index)
            if resp is None:
                break
            values.append(resp[2])
            index += 1
        return values

    def items(self):
        # return list(self.iteritems()) # that can't be optimized by psyco
        items = list()
        index = 0
        while 1:
            resp = win32.RegEnumValue(self._handle, index)
            if resp is None:
                break
            items.append( (resp[0], resp[2]) )
            index += 1
        return items

    def clear(self):
        while 1:
            resp = win32.RegEnumValue(self._handle, 0, False)
            if resp is None:
                break
            win32.RegDeleteValue(self._handle, resp[0])

    def __str__(self):
        return self['']

    def __unicode__(self):
        return self[u'']

    def __repr__(self):
        return '<Registry key: "%s">' % self._path

    def child(self, subkey):
        """
        Retrieves a subkey for this Registry key, given its name.
        
        @type  subkey: str
        @param subkey: Name of the subkey.
        
        @rtype:  L{RegistryKey}
        @return: Subkey.
        """
        path = self._path + '\\' + subkey
        handle = win32.RegOpenKey(self._handle, subkey)
        return RegistryKey(path, handle)

    # TODO: add methods children() and iterchildren()

    def flush(self):
        """
        Flushes changes immediately to disk.
        
        This method is normally not needed, as the Registry writes changes
        to disk by itself. This mechanism is provided to ensure the write
        happens immediately, as opposed to whenever the OS wants to.
        
        @warn: Calling this method too often may degrade performance.
        """
        win32.RegFlushKey(self._handle)

#==============================================================================

# TODO: possibly cache the RegistryKey objects
# to avoid opening and closing handles many times on code sequences like this:
#
# r = Registry()
# r['HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Run']['Example 1'] = 'example1.exe'
# r['HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Run']['Example 2'] = 'example2.exe'
# r['HKLM\\Software\\Microsoft\\Windows NT\\CurrentVersion\\Run']['Example 3'] = 'example3.exe'

# TODO: support for access flags?
# TODO: should be possible to disable the safety checks (see __delitem__)

# TODO: workaround for an API bug described by a user in MSDN
#
# http://msdn.microsoft.com/en-us/library/windows/desktop/aa379776(v=vs.85).aspx
#
# Apparently RegDeleteTree won't work remotely from Win7 to WinXP, and the only
# solution is to recursively call RegDeleteKey.

class Registry (_RegistryContainer):
    """
    Exposes the Windows Registry as a Python container.

    @type machine: str or None
    @ivar machine: For a remote Registry, the machine name.
        For a local Registry, the value is C{None}.
    """

    _hives_by_name = {
        
        # Short names
        'HKCR' : win32.HKEY_CLASSES_ROOT,
        'HKCU' : win32.HKEY_CURRENT_USER,
        'HKLM' : win32.HKEY_LOCAL_MACHINE,
        'HKU'  : win32.HKEY_USERS,
        'HKPD' : win32.HKEY_PERFORMANCE_DATA,
        'HKCC' : win32.HKEY_CURRENT_CONFIG,
        
        # Long names
        'HKEY_CLASSES_ROOT'     : win32.HKEY_CLASSES_ROOT,
        'HKEY_CURRENT_USER'     : win32.HKEY_CURRENT_USER,
        'HKEY_LOCAL_MACHINE'    : win32.HKEY_LOCAL_MACHINE,
        'HKEY_USERS'            : win32.HKEY_USERS,
        'HKEY_PERFORMANCE_DATA' : win32.HKEY_PERFORMANCE_DATA,
        'HKEY_CURRENT_CONFIG'   : win32.HKEY_CURRENT_CONFIG,
    }

    _hives_by_value = {
        win32.HKEY_CLASSES_ROOT     : 'HKEY_CLASSES_ROOT',
        win32.HKEY_CURRENT_USER     : 'HKEY_CURRENT_USER',
        win32.HKEY_LOCAL_MACHINE    : 'HKEY_LOCAL_MACHINE',
        win32.HKEY_USERS            : 'HKEY_USERS',
        win32.HKEY_PERFORMANCE_DATA : 'HKEY_PERFORMANCE_DATA',
        win32.HKEY_CURRENT_CONFIG   : 'HKEY_CURRENT_CONFIG',
    }

    _hives = sorted(_hives_by_value.itervalues())

    def __init__(self, machine = None):
        """
        Opens a local or remote registry.
        
        @type  machine: str
        @param machine: Optional machine name. If C{None} it opens the local
            registry.
        """
        self._machine = machine
        self._remote_hives = {}

    @property
    def machine(self):
        return self._machine

    def _parse_path(self, path):
        """
        Parses a Registry path and returns the hive and key.
        
        @rtype:  tuple( int, str )
        @return: Tuple containing the hive handle and the subkey path.
            For a local Registry, the hive handle is an integer.
            For a remote Registry, the hive handle is a L{RegistryKeyHandle}.
        """
        if '\\' in path:
            p = path.find('\\')
            hive = path[:p]
            path = path[p+1:]
        else:
            hive = path
            path = None
        handle = self._hives_by_name[hive]
        if self._machine is not None:
            handle = self._connect_hive(hive)
        return handle, path

    def _connect_hive(self, hive):
        """
        Connect to the specified hive of a remote Registry.
        
        @note: The connection will be cached, to close all connections and
            erase this cache call the L{close} method.
        
        @type  hive: int
        @param hive: Hive to connect to.
        
        @rtype:  L{win32.RegistryKeyHandle}
        @return: Open handle to the remote Registry hive.
        """
        try:
            handle = self._remote_hives[hive]
        except KeyError:
            handle = win32.RegConnectRegistry(self._machine, hive)
            self._remote_hives[hive] = handle
        return handle

    def close(self):
        """
        Closes all open connections to the remote Registry.
        
        No exceptions are raised, even if an error occurs.
        
        This method has no effect when opening the local Registry.
        
        The remote Registry will still be accessible after calling this method
        (new connections will be opened automatically on access).
        """
        while self._remote_hives:
            hive = self._remote_hives.popitem()[1]
            try:
                hive.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __repr__(self):
        if self._machine:
            return '<Remote Registry at "%s">' % self._machine
        return '<Local Registry>'

    def __contains__(self, path):
        hive, subpath = self._parse_path(path)
        try:
            with win32.RegOpenKey(hive, subpath):
                return True
        except WindowsError, e:
            if win32.winerror(e) == win32.ERROR_FILE_NOT_FOUND:
                return False
            raise

    def __getitem__(self, path):
        hive, subpath = self._parse_path(path)
        try:
            handle = win32.RegOpenKey(hive, subpath)
        except WindowsError, e:
            if win32.winerror(e) == win32.ERROR_FILE_NOT_FOUND:
                raise KeyError(path)
            raise
        return RegistryKey(path, handle)

    def __setitem__(self, path, value):
        do_copy = isinstance(value, RegistryKey)
        if not do_copy and not isinstance(value, str)    \
                       and not isinstance(value, unicode):
            if isinstance(value, object):
                t = value.__class__.__name__
            else:
                t = type(value)
            raise TypeError("Expected string or RegistryKey, got %s" % t)
        hive, subpath = self._parse_path(path)
        with win32.RegCreateKey(hive, subpath) as handle:
            if do_copy:
                win32.RegCopyTree(value.handle, None, handle)
            else:
                win32.RegSetValueEx(handle, None, value)

    # XXX FIXME currently not working!
    # It's probably best to call RegDeleteKey recursively, even if slower.
    def __delitem__(self, path):
        hive, subpath = self._parse_path(path)
        if not subpath:
            raise TypeError(
                "Are you SURE you want to wipe out an entire hive?!"
                " Call win32.RegDeleteTree() directly if you must...")
        try:
            win32.RegDeleteTree(hive, subpath)
        except WindowsError, e:
            if win32.winerror(e) == win32.ERROR_FILE_NOT_FOUND:
                raise KeyError(path)
            raise

    def create(self, path):
        """
        Creates a new Registry key.
        
        @type  path: str
        @param path: Registry key path.
        
        @rtype:  L{RegistryKey}
        @return: The newly created Registry key.
        """
        hive, subpath = self._parse_path(path)
        handle = win32.RegCreateKey(hive, subpath)
        return RegistryKey(path, handle)

    def subkeys(self, path):
        """
        Returns a list of subkeys for the given Registry key.
        
        @type  path: str
        @param path: Registry key path.
        
        @rtype:  list(str)
        @return: List of subkey names.
        """
        result = list()
        hive, subpath = self._parse_path(path)
        with win32.RegOpenKey(hive, subpath) as handle:
            index = 0
            while 1:
                name = win32.RegEnumKey(handle, index)
                if name is None:
                    break
                result.append(name)
                index += 1
        return result

    def iterate(self, path):
        """
        Returns a recursive iterator on the specified key and its subkeys.
        
        @type  path: str
        @param path: Registry key path.
        
        @rtype:  iterator
        @return: Recursive iterator that returns Registry key paths.
        
        @raise KeyError: The specified path does not exist.
        """
        if path.endswith('\\'):
            path = path[:-1]
        if not self.has_key(path):
            raise KeyError(path)
        stack = collections.deque()
        stack.appendleft(path)
        return self.__iterate(stack)

    def iterkeys(self):
        """
        Returns an iterator that crawls the entire Windows Registry.
        """
        stack = collections.deque(self._hives)
        stack.reverse()
        return self.__iterate(stack)

    def __iterate(self, stack):
        while stack:
            path = stack.popleft()
            yield path
            try:
                subkeys = self.subkeys(path)
            except WindowsError:
                continue
            prefix = path + '\\'
            subkeys = [prefix + name for name in subkeys]
            stack.extendleft(subkeys)
