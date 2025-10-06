import unittest
import os
from unittest.mock import patch
from src.config import Config

class TestConfig(unittest.TestCase):
    
    def test_config_attributes_exist(self):
        """Проверяем, что все ожидаемые атрибуты конфигурации существуют"""
        self.assertTrue(hasattr(Config, 'MS_CLIENT_ID'))
        self.assertTrue(hasattr(Config, 'AUTHORITY'))
        self.assertTrue(hasattr(Config, 'SCOPE'))
        self.assertTrue(hasattr(Config, 'CACHE_FILE'))
        self.assertTrue(hasattr(Config, 'KAITEN_TOKEN'))
        self.assertTrue(hasattr(Config, 'KAITEN_DOMAIN'))
        self.assertTrue(hasattr(Config, 'KAITEN_SPACE_ID'))
        self.assertTrue(hasattr(Config, 'KAITEN_BOARD_ID'))
        self.assertTrue(hasattr(Config, 'KAITEN_COLUMN_ID'))
        self.assertTrue(hasattr(Config, 'KAITEN_API_BASE'))
        self.assertTrue(hasattr(Config, 'MAPPING_FILE'))
        self.assertTrue(hasattr(Config, 'SYNC_LIST_NAME'))
    
    @patch.dict(os.environ, {
        'MS_CLIENT_ID': 'test_client_id',
        'KAITEN_API_TOKEN': 'test_token',
        'KAITEN_DOMAIN': 'test.domain.com',
        'KAITEN_SPACE_ID': '123',
        'KAITEN_BOARD_ID': '456',
        'KAITEN_COLUMN_ID': '789'
    })
    def test_validate_with_all_env_vars(self):
        """Проверяем валидацию при наличии всех переменных окружения"""
        # Перезагружаем Config, чтобы он использовал mocked переменные
        import importlib
        import src.config
        importlib.reload(src.config)
        from src.config import Config as ReloadedConfig
        
        self.assertTrue(ReloadedConfig.validate())
    
    def test_get_missing_vars(self):
        """Проверяем получение списка отсутствующих переменных"""
        missing_vars = Config.get_missing_vars()
        expected_vars = [
            'MS_CLIENT_ID', 'KAITEN_API_TOKEN', 'KAITEN_DOMAIN', 
            'KAITEN_SPACE_ID', 'KAITEN_BOARD_ID', 'KAITEN_COLUMN_ID'
        ]
        self.assertEqual(set(missing_vars), set(expected_vars))


if __name__ == '__main__':
    unittest.main()