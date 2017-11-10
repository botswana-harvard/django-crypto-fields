import copy
import sys

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA as RSA_PUBLIC_KEY
from Crypto.Util import number
from django.apps import apps as django_apps
from django.core.exceptions import AppRegistryNotReady
from django_crypto_fields.exceptions import DjangoCryptoFieldsKeysAlreadyLoaded

from .constants import RSA, AES, SALT, PRIVATE
from .key_path_handler import KeyPathHandler


class Keys:

    """
    Class to prepare RSA, AES keys for use by field classes.

        * Keys are imported through the AppConfig __init__ method.
        * Keys are create through the AppConfig __init__ method, if necessary.
    """

    keys_are_ready = False
    rsa_key_info = {}
    key_path_handler_cls = KeyPathHandler

    def __init__(self, key_path=None, key_prefix=None):
        key_path_handler = self.key_path_handler_cls(
            key_path=key_path, key_prefix=key_prefix)
        self.key_path = key_path_handler.key_path
        self.key_filenames = key_path_handler.key_filenames
        self._keys = copy.deepcopy(key_path_handler.key_filenames)
        self.rsa_modes_supported = sorted([k for k in self._keys[RSA]])
        self.aes_modes_supported = sorted([k for k in self._keys[AES]])

    def load_keys(self):
        """Loads all keys defined in self.key_filenames.
        """
        try:
            if django_apps.get_app_config('django_crypto_fields').encryption_keys:
                raise DjangoCryptoFieldsKeysAlreadyLoaded()
        except (AppRegistryNotReady, AttributeError):
            pass
        if not self.keys_are_ready:
            sys.stdout.write(f' * loading keys from {self.key_path}\n')
            for mode, keys in self.key_filenames[RSA].items():
                for key in keys:
                    sys.stdout.write(
                        f' * loading {RSA}.{mode}.{key} ...\r')
                    self.load_rsa_key(mode, key)
                    sys.stdout.write(
                        f' * loading {RSA}.{mode}.{key} ... Done.\n')
            for mode in self.key_filenames[AES]:
                sys.stdout.write(f' * loading {AES}.{mode} ...\r')
                self.load_aes_key(mode)
                sys.stdout.write(
                    f' * loading {AES}.{mode} ... Done.\n')
            for mode in self.key_filenames[SALT]:
                sys.stdout.write(f' * loading {SALT}.{mode} ...\r')
                self.load_salt_key(mode, key)
                sys.stdout.write(
                    f' * loading {SALT}.{mode} ... Done.\n')
            self.keys_are_ready = True

    def load_rsa_key(self, mode, key):
        """Loads an RSA key into _keys.
        """
        key_file = self.key_filenames[RSA][mode][key]
        with open(key_file, 'rb') as frsa:
            rsa_key = RSA_PUBLIC_KEY.importKey(frsa.read())
            rsa_key = PKCS1_OAEP.new(rsa_key)
            self._keys[RSA][mode][key] = rsa_key
            self.update_rsa_key_info(rsa_key, mode)
        setattr(self, RSA + '_' + mode + '_' + key + '_key', rsa_key)
        return key_file

    def load_aes_key(self, mode):
        """Decrypts and loads an AES key into _keys.

        Note: AES does not use a public key.
        """
        key = PRIVATE
        rsa_key = self._keys[RSA][mode][key]
        try:
            key_file = self.key_filenames[AES][mode][key]
        except KeyError:
            raise
        with open(key_file, 'rb') as faes:
            aes_key = rsa_key.decrypt(faes.read())
        self._keys[AES][mode][key] = aes_key
        setattr(self, AES + '_' + mode + '_' + key + '_key', aes_key)
        return key_file

    def load_salt_key(self, mode, key):
        """Decrypts and loads a salt key into _keys.
        """
        attr = SALT + '_' + mode + '_' + PRIVATE
        rsa_key = self._keys[RSA][mode][PRIVATE]
        key_file = self.key_filenames[SALT][mode][PRIVATE]
        with open(key_file, 'rb') as fsalt:
            salt = rsa_key.decrypt(fsalt.read())
            setattr(self, attr, salt)
        return key_file

    def update_rsa_key_info(self, rsa_key, mode):
        """Stores info about the RSA key.
        """
        modBits = number.size(rsa_key._key.n)
        self.rsa_key_info[mode] = {'bits': modBits}
        k = number.ceil_div(modBits, 8)
        self.rsa_key_info[mode].update({'bytes': k})
        hLen = rsa_key._hashObj.digest_size
        self.rsa_key_info[mode].update(
            {'max_message_length': k - (2 * hLen) - 2})
