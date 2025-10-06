import unittest
import os
import json
from src.utils import (
    load_mapping, save_mapping, 
    compute_todo_hash, compute_kaiten_hash,
    todo_date_to_kaiten_date, kaiten_date_to_todo_date
)

class TestUtils(unittest.TestCase):
    
    def test_compute_todo_hash(self):
        task = {
            "title": "Test task",
            "body": {"content": "Test description"},
            "dueDateTime": {"dateTime": "2023-12-31T10:00:00.00000"},
            "status": "notStarted"
        }
        expected_hash = "Test task|Test description|2023-12-31|notStarted"
        self.assertEqual(compute_todo_hash(task), expected_hash)
    
    def test_compute_kaiten_hash(self):
        card = {
            "title": "Test card",
            "description": "Test description",
            "due_date": "2023-12-31",
            "state": 1  # notStarted
        }
        expected_hash = "Test card|Test description|2023-12-31|notStarted"
        self.assertEqual(compute_kaiten_hash(card), expected_hash)
    
    def test_todo_date_to_kaiten_date(self):
        todo_date = "2023-12-31T10:00:00.0000000"
        expected_kaiten_date = "2023-12-31"
        self.assertEqual(todo_date_to_kaiten_date(todo_date), expected_kaiten_date)
        
        self.assertIsNone(todo_date_to_kaiten_date(None))
    
    def test_kaiten_date_to_todo_date(self):
        kaiten_date = "2023-12-31"
        expected_todo_date = "2023-12-31T10:00.0000000"
        self.assertEqual(kaiten_date_to_todo_date(kaiten_date), expected_todo_date)
        
        self.assertIsNone(kaiten_date_to_todo_date(None))
    
    def test_mapping_functions(self):
        test_mapping = {"test_id": {"kaiten_card_id": 123}}
        test_file = "test_mapping.json"
        
        # Сохраняем тестовое сопоставление
        save_mapping(test_mapping, test_file)
        
        # Загружаем и проверяем
        loaded_mapping = load_mapping(test_file)
        self.assertEqual(loaded_mapping, test_mapping)
        
        # Удаляем тестовый файл
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == '__main__':
    unittest.main()