import os
import pytest
from pytest import fixture
from mydb import MyDB

# Test file path for isolation
TEST_DB_FILE = "test_mydb_temp.pkl"


@fixture
def clean_db():
    """Fixture to ensure clean state before each test"""
    # Setup: Remove test file if it exists
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)
    
    yield TEST_DB_FILE
    
    # Teardown: Clean up after test
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


def describe_MyDB_init():
    """Test suite for MyDB.__init__() method"""
    
    def it_creates_new_file_when_file_does_not_exist(clean_db):
        """Should create a new database file if it doesn't exist"""
        # Verify file doesn't exist before
        assert not os.path.exists(clean_db)
        
        # Initialize database
        db = MyDB(clean_db)
        
        # Verify file was created
        assert os.path.exists(clean_db)
    
    def it_initializes_with_empty_array_when_file_does_not_exist(clean_db):
        """Should initialize new file with empty array"""
        db = MyDB(clean_db)
        
        # Load and verify empty array
        result = db.loadStrings()
        assert result == []
    
    def it_does_not_overwrite_existing_file(clean_db):
        """Should not overwrite file if it already exists"""
        # Create initial database with data
        db1 = MyDB(clean_db)
        db1.saveString("existing_data")
        
        # Create new instance with same filename
        db2 = MyDB(clean_db)
        
        # Verify existing data is preserved
        result = db2.loadStrings()
        assert "existing_data" in result


def describe_MyDB_loadStrings():
    """Test suite for MyDB.loadStrings() method"""
    
    def it_returns_empty_array_from_new_database(clean_db):
        """Should return empty array when database is newly created"""
        db = MyDB(clean_db)
        result = db.loadStrings()
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def it_returns_saved_strings(clean_db):
        """Should return all previously saved strings"""
        db = MyDB(clean_db)
        test_strings = ["first", "second", "third"]
        db.saveStrings(test_strings)
        
        result = db.loadStrings()
        assert result == test_strings
    
    def it_returns_strings_in_correct_order(clean_db):
        """Should maintain order of strings"""
        db = MyDB(clean_db)
        db.saveString("alpha")
        db.saveString("beta")
        db.saveString("gamma")
        
        result = db.loadStrings()
        assert result == ["alpha", "beta", "gamma"]
    
    def it_returns_independent_copy_of_data(clean_db):
        """Should return data that can be modified without affecting stored data"""
        db = MyDB(clean_db)
        db.saveStrings(["original"])
        
        # Load and modify returned array
        result = db.loadStrings()
        result.append("modified")
        
        # Verify stored data unchanged
        stored = db.loadStrings()
        assert stored == ["original"]


def describe_MyDB_saveStrings():
    """Test suite for MyDB.saveStrings() method"""
    
    def it_saves_empty_array(clean_db):
        """Should save empty array successfully"""
        db = MyDB(clean_db)
        db.saveStrings([])
        
        result = db.loadStrings()
        assert result == []
    
    def it_saves_single_string(clean_db):
        """Should save array with single string"""
        db = MyDB(clean_db)
        db.saveStrings(["single"])
        
        result = db.loadStrings()
        assert result == ["single"]
    
    def it_saves_multiple_strings(clean_db):
        """Should save array with multiple strings"""
        db = MyDB(clean_db)
        test_data = ["one", "two", "three", "four"]
        db.saveStrings(test_data)
        
        result = db.loadStrings()
        assert result == test_data
    
    def it_overwrites_existing_data(clean_db):
        """Should replace existing data with new array"""
        db = MyDB(clean_db)
        db.saveStrings(["old", "data"])
        db.saveStrings(["new", "data"])
        
        result = db.loadStrings()
        assert result == ["new", "data"]
        assert len(result) == 2
    
    def it_persists_data_across_instances(clean_db):
        """Should persist data that can be loaded by new instance"""
        db1 = MyDB(clean_db)
        db1.saveStrings(["persistent"])
        
        # Create new instance
        db2 = MyDB(clean_db)
        result = db2.loadStrings()
        assert result == ["persistent"]
    
    def it_saves_strings_with_special_characters(clean_db):
        """Should handle strings with special characters"""
        db = MyDB(clean_db)
        special_strings = ["hello\nworld", "tab\there", "quote\"test"]
        db.saveStrings(special_strings)
        
        result = db.loadStrings()
        assert result == special_strings


def describe_MyDB_saveString():
    """Test suite for MyDB.saveString() method"""
    
    def it_appends_string_to_empty_database(clean_db):
        """Should add string to empty database"""
        db = MyDB(clean_db)
        db.saveString("first")
        
        result = db.loadStrings()
        assert result == ["first"]
    
    def it_appends_string_to_existing_data(clean_db):
        """Should append string to end of existing data"""
        db = MyDB(clean_db)
        db.saveStrings(["existing"])
        db.saveString("appended")
        
        result = db.loadStrings()
        assert result == ["existing", "appended"]
    
    def it_appends_multiple_strings_sequentially(clean_db):
        """Should maintain order when appending multiple strings"""
        db = MyDB(clean_db)
        db.saveString("first")
        db.saveString("second")
        db.saveString("third")
        
        result = db.loadStrings()
        assert result == ["first", "second", "third"]
    
    def it_preserves_existing_strings_when_appending(clean_db):
        """Should not modify existing strings when appending new one"""
        db = MyDB(clean_db)
        db.saveStrings(["one", "two"])
        db.saveString("three")
        
        result = db.loadStrings()
        assert "one" in result
        assert "two" in result
        assert "three" in result
        assert len(result) == 3
    
    def it_allows_duplicate_strings(clean_db):
        """Should allow saving duplicate strings"""
        db = MyDB(clean_db)
        db.saveString("duplicate")
        db.saveString("duplicate")
        
        result = db.loadStrings()
        assert result == ["duplicate", "duplicate"]
    
    def it_handles_empty_string(clean_db):
        """Should successfully save empty string"""
        db = MyDB(clean_db)
        db.saveString("")
        
        result = db.loadStrings()
        assert result == [""]
    
    def it_handles_unicode_strings(clean_db):
        """Should handle unicode characters"""
        db = MyDB(clean_db)
        db.saveString("Hello 世界 🌍")
        
        result = db.loadStrings()
        assert result == ["Hello 世界 🌍"]
    
    def it_persists_appended_string_across_instances(clean_db):
        """Should persist appended string for new instance"""
        db1 = MyDB(clean_db)
        db1.saveString("persistent")
        
        db2 = MyDB(clean_db)
        result = db2.loadStrings()
        assert "persistent" in result
