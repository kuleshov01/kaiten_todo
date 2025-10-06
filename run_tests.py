"""
Скрипт для запуска всех тестов проекта
"""
import unittest
import sys
import os

if __name__ == '__main__':
    # Добавляем директорию src в путь Python, чтобы можно было импортировать модули
    src_dir = os.path.join(os.path.dirname(__file__), 'src')
    sys.path.insert(0, src_dir)
    
    # Запускаем тесты из директории tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Возвращаем код завершения для CI/CD
    sys.exit(0 if result.wasSuccessful() else 1)