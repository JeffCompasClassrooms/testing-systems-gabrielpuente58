import os
import shutil
import subprocess
import time
import json
import requests
import socket
from pytest import fixture

# Server configuration
DB_FILE = "squirrel_db.db"
TEMPLATE_DB_FILE = "empty_squirrel_db.db"


def find_free_port():
    """Find an available port to use for the test server"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@fixture(scope="session")
def server():
    """Start server once for all tests on a free port"""
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find a free port
    port = find_free_port()
    server_url = f"http://127.0.0.1:{port}"
    
    # Find Python executable
    import sys
    python_executable = sys.executable
    
    # Create a temporary modified server file with the new port
    with open(os.path.join(workspace_dir, "squirrel_server.py"), "r") as f:
        server_code = f.read()
    
    # Replace the port in the server code
    modified_code = server_code.replace(
        'listen = ("127.0.0.1", 8080)',
        f'listen = ("127.0.0.1", {port})'
    )
    
    temp_server_file = os.path.join(workspace_dir, "test_squirrel_server_temp.py")
    with open(temp_server_file, "w") as f:
        f.write(modified_code)
    
    # Start the server on the free port
    server_process = subprocess.Popen(
        [python_executable, temp_server_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=workspace_dir
    )
    
    # Wait for server to start
    max_retries = 30
    server_started = False
    for i in range(max_retries):
        try:
            response = requests.get(f"{server_url}/squirrels", timeout=1)
            server_started = True
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            time.sleep(0.3)
    
    if not server_started:
        server_process.kill()
        if os.path.exists(temp_server_file):
            os.remove(temp_server_file)
        raise Exception("Server failed to start")
    
    yield (server_process, server_url)
    
    # Cleanup
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
    
    # Remove temporary server file
    if os.path.exists(temp_server_file):
        os.remove(temp_server_file)


@fixture
def reset_database(server):
    """Reset database to clean state before each test"""
    server_process, server_url = server
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(workspace_dir, DB_FILE)
    template_path = os.path.join(workspace_dir, TEMPLATE_DB_FILE)
    
    # Copy template database
    if os.path.exists(db_path):
        os.remove(db_path)
    shutil.copy(template_path, db_path)
    
    # Small delay to ensure file system sync
    time.sleep(0.15)
    
    yield server_url
    
    # Cleanup after test (optional, but ensures clean state)
    time.sleep(0.1)


def describe_GET_squirrels_list():
    """Test suite for GET /squirrels - List all squirrels"""
    
    def it_returns_200_status_code(reset_database):
        """Should return 200 OK status"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels")
        assert response.status_code == 200
    
    def it_returns_json_content_type(reset_database):
        """Should return application/json content type"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels")
        assert response.headers["Content-Type"] == "application/json"
    
    def it_returns_empty_array_when_no_squirrels(reset_database):
        """Should return empty array when database is empty"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def it_returns_array_of_squirrels_after_creation(reset_database):
        """Should return all created squirrels"""
        server_url = reset_database
        # Create squirrels
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        requests.post(f"{server_url}/squirrels", data={"name": "Tiny", "size": "small"})
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert len(data) == 2
    
    def it_returns_squirrels_with_all_fields(reset_database):
        """Should return squirrels with id, name, and size fields"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        squirrel = data[0]
        
        assert "id" in squirrel
        assert "name" in squirrel
        assert "size" in squirrel
        assert squirrel["name"] == "Fluffy"
        assert squirrel["size"] == "large"
    
    def it_returns_squirrels_ordered_by_id(reset_database):
        """Should return squirrels sorted by id"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "First", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Second", "size": "medium"})
        requests.post(f"{server_url}/squirrels", data={"name": "Third", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        
        assert data[0]["name"] == "First"
        assert data[1]["name"] == "Second"
        assert data[2]["name"] == "Third"


def describe_GET_squirrels_retrieve():
    """Test suite for GET /squirrels/{id} - Retrieve single squirrel"""
    
    def it_returns_200_status_code_for_existing_squirrel(reset_database):
        """Should return 200 OK for existing squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        assert response.status_code == 200
    
    def it_returns_json_content_type_for_existing_squirrel(reset_database):
        """Should return application/json content type"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        assert response.headers["Content-Type"] == "application/json"
    
    def it_returns_correct_squirrel_data(reset_database):
        """Should return correct squirrel object"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        
        assert data["id"] == 1
        assert data["name"] == "Fluffy"
        assert data["size"] == "large"
    
    def it_returns_correct_squirrel_when_multiple_exist(reset_database):
        """Should return the specific requested squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "First", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Second", "size": "large"})
        requests.post(f"{server_url}/squirrels", data={"name": "Third", "size": "medium"})
        
        response = requests.get(f"{server_url}/squirrels/2")
        data = response.json()
        
        assert data["id"] == 2
        assert data["name"] == "Second"
        assert data["size"] == "large"
    
    def it_returns_404_for_nonexistent_squirrel(reset_database):
        """Should return 404 when squirrel doesn't exist"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels/999")
        assert response.status_code == 404
    
    def it_returns_text_plain_content_type_for_404(reset_database):
        """Should return text/plain for 404 response"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels/999")
        assert response.headers["Content-Type"] == "text/plain"
    
    def it_returns_404_message_for_nonexistent_squirrel(reset_database):
        """Should return '404 Not Found' message"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels/999")
        assert response.text == "404 Not Found"


def describe_POST_squirrels_create():
    """Test suite for POST /squirrels - Create new squirrel"""
    
    def it_returns_201_status_code(reset_database):
        """Should return 201 Created status"""
        server_url = reset_database
        response = requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        assert response.status_code == 201
    
    def it_creates_squirrel_in_database(reset_database):
        """Should persist squirrel in database"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        # Verify by retrieving
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Fluffy"
    
    def it_creates_squirrel_with_correct_name(reset_database):
        """Should save squirrel with provided name"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "TestName", "size": "medium"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["name"] == "TestName"
    
    def it_creates_squirrel_with_correct_size(reset_database):
        """Should save squirrel with provided size"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "extra-large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["size"] == "extra-large"
    
    def it_assigns_id_to_created_squirrel(reset_database):
        """Should assign an id to new squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["id"] == 1
    
    def it_creates_multiple_squirrels_with_unique_ids(reset_database):
        """Should assign unique ids to multiple squirrels"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "First", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Second", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert data[0]["id"] == 1
        assert data[1]["id"] == 2
    
    def it_creates_squirrel_retrievable_by_id(reset_database):
        """Should create squirrel that can be retrieved by id"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Retrievable", "size": "medium"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Retrievable"
    
    def it_rejects_squirrel_with_empty_size(reset_database):
        """Should not allow creating squirrel with empty size"""
        server_url = reset_database
        response = requests.post(f"{server_url}/squirrels", data={"name": "TestSquirrel", "size": ""})
        
        assert response.status_code == 400
    
    def it_rejects_squirrel_with_missing_size(reset_database):
        """Should return 400 when size field is missing"""
        server_url = reset_database
        response = requests.post(f"{server_url}/squirrels", data={"name": "TestSquirrel"})
        
        assert response.status_code == 400
    
    def it_rejects_squirrel_with_missing_name(reset_database):
        """Should return 400 when name field is missing"""
        server_url = reset_database
        response = requests.post(f"{server_url}/squirrels", data={"size": "medium"})
        
        assert response.status_code == 400


def describe_PUT_squirrels_update():
    """Test suite for PUT /squirrels/{id} - Update squirrel"""
    
    def it_returns_204_status_code_for_successful_update(reset_database):
        """Should return 204 No Content for successful update"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Original", "size": "small"})
        
        response = requests.put(f"{server_url}/squirrels/1", data={"name": "Updated", "size": "large"})
        assert response.status_code == 204
    
    def it_updates_squirrel_name(reset_database):
        """Should update the squirrel's name"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Original", "size": "small"})
        requests.put(f"{server_url}/squirrels/1", data={"name": "NewName", "size": "small"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["name"] == "NewName"
    
    def it_updates_squirrel_size(reset_database):
        """Should update the squirrel's size"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Fluffy", "size": "small"})
        requests.put(f"{server_url}/squirrels/1", data={"name": "Fluffy", "size": "huge"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["size"] == "huge"
    
    def it_updates_both_name_and_size(reset_database):
        """Should update both name and size together"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Original", "size": "small"})
        requests.put(f"{server_url}/squirrels/1", data={"name": "Changed", "size": "enormous"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["name"] == "Changed"
        assert data["size"] == "enormous"
    
    def it_preserves_squirrel_id_after_update(reset_database):
        """Should not change the squirrel's id"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Original", "size": "small"})
        requests.put(f"{server_url}/squirrels/1", data={"name": "Updated", "size": "large"})
        
        response = requests.get(f"{server_url}/squirrels/1")
        data = response.json()
        assert data["id"] == 1
    
    def it_updates_correct_squirrel_when_multiple_exist(reset_database):
        """Should update only the specified squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "First", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Second", "size": "medium"})
        requests.post(f"{server_url}/squirrels", data={"name": "Third", "size": "large"})
        
        requests.put(f"{server_url}/squirrels/2", data={"name": "Modified", "size": "huge"})
        
        # Verify correct squirrel updated
        response = requests.get(f"{server_url}/squirrels/2")
        data = response.json()
        assert data["name"] == "Modified"
        
        # Verify others unchanged
        response1 = requests.get(f"{server_url}/squirrels/1")
        assert response1.json()["name"] == "First"
        response3 = requests.get(f"{server_url}/squirrels/3")
        assert response3.json()["name"] == "Third"
    
    def it_returns_404_for_nonexistent_squirrel(reset_database):
        """Should return 404 when updating nonexistent squirrel"""
        server_url = reset_database
        response = requests.put(f"{server_url}/squirrels/999", data={"name": "Ghost", "size": "none"})
        assert response.status_code == 404
    
    def it_returns_404_message_when_updating_nonexistent_squirrel(reset_database):
        """Should return '404 Not Found' message"""
        server_url = reset_database
        response = requests.put(f"{server_url}/squirrels/999", data={"name": "Ghost", "size": "none"})
        assert response.text == "404 Not Found"


def describe_DELETE_squirrels():
    """Test suite for DELETE /squirrels/{id} - Delete squirrel"""
    
    def it_returns_204_status_code_for_successful_deletion(reset_database):
        """Should return 204 No Content for successful deletion"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "ToDelete", "size": "small"})
        
        response = requests.delete(f"{server_url}/squirrels/1")
        assert response.status_code == 204
    
    def it_removes_squirrel_from_database(reset_database):
        """Should remove squirrel so it's not in list"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "ToDelete", "size": "small"})
        requests.delete(f"{server_url}/squirrels/1")
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert len(data) == 0
    
    def it_makes_squirrel_unretrievable_after_deletion(reset_database):
        """Should return 404 when retrieving deleted squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "ToDelete", "size": "small"})
        requests.delete(f"{server_url}/squirrels/1")
        
        response = requests.get(f"{server_url}/squirrels/1")
        assert response.status_code == 404
    
    def it_deletes_correct_squirrel_when_multiple_exist(reset_database):
        """Should delete only the specified squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Keep1", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Delete", "size": "medium"})
        requests.post(f"{server_url}/squirrels", data={"name": "Keep2", "size": "large"})
        
        requests.delete(f"{server_url}/squirrels/2")
        
        # Verify correct one deleted
        response = requests.get(f"{server_url}/squirrels/2")
        assert response.status_code == 404
        
        # Verify others remain
        response1 = requests.get(f"{server_url}/squirrels/1")
        assert response1.status_code == 200
        response3 = requests.get(f"{server_url}/squirrels/3")
        assert response3.status_code == 200
    
    def it_reduces_list_count_after_deletion(reset_database):
        """Should reduce total count in list endpoint"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "One", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "Two", "size": "medium"})
        requests.post(f"{server_url}/squirrels", data={"name": "Three", "size": "large"})
        
        requests.delete(f"{server_url}/squirrels/2")
        
        response = requests.get(f"{server_url}/squirrels")
        data = response.json()
        assert len(data) == 2
    
    def it_returns_404_for_nonexistent_squirrel(reset_database):
        """Should return 404 when deleting nonexistent squirrel"""
        server_url = reset_database
        response = requests.delete(f"{server_url}/squirrels/999")
        assert response.status_code == 404
    
    def it_returns_404_message_when_deleting_nonexistent_squirrel(reset_database):
        """Should return '404 Not Found' message"""
        server_url = reset_database
        response = requests.delete(f"{server_url}/squirrels/999")
        assert response.text == "404 Not Found"


def describe_failure_conditions():
    """Test suite for various failure scenarios (404 responses)"""
    
    def it_returns_404_for_invalid_resource_name_on_GET(reset_database):
        """Should return 404 for GET on unknown resource"""
        server_url = reset_database
        response = requests.get(f"{server_url}/invalid")
        assert response.status_code == 404
    
    def it_returns_404_for_invalid_resource_name_on_POST(reset_database):
        """Should return 404 for POST on unknown resource"""
        server_url = reset_database
        response = requests.post(f"{server_url}/invalid", data={"name": "test", "size": "small"})
        assert response.status_code == 404
    
    def it_returns_404_for_invalid_resource_name_on_PUT(reset_database):
        """Should return 404 for PUT on unknown resource"""
        server_url = reset_database
        response = requests.put(f"{server_url}/invalid/1", data={"name": "test", "size": "small"})
        assert response.status_code == 404
    
    def it_returns_404_for_invalid_resource_name_on_DELETE(reset_database):
        """Should return 404 for DELETE on unknown resource"""
        server_url = reset_database
        response = requests.delete(f"{server_url}/invalid/1")
        assert response.status_code == 404
    
    def it_returns_404_for_POST_with_id_parameter(reset_database):
        """Should return 404 for POST /squirrels/{id}"""
        server_url = reset_database
        response = requests.post(f"{server_url}/squirrels/1", data={"name": "test", "size": "small"})
        assert response.status_code == 404
    
    def it_returns_404_for_PUT_without_id_parameter(reset_database):
        """Should return 404 for PUT /squirrels without id"""
        server_url = reset_database
        response = requests.put(f"{server_url}/squirrels", data={"name": "test", "size": "small"})
        assert response.status_code == 404
    
    def it_returns_404_for_DELETE_without_id_parameter(reset_database):
        """Should return 404 for DELETE /squirrels without id"""
        server_url = reset_database
        response = requests.delete(f"{server_url}/squirrels")
        assert response.status_code == 404
    
    def it_returns_404_for_empty_path(reset_database):
        """Should return 404 for root path"""
        server_url = reset_database
        response = requests.get(f"{server_url}/")
        assert response.status_code == 404
    
    def it_returns_404_for_nested_invalid_paths(reset_database):
        """Should return 404 for deeply nested invalid paths"""
        server_url = reset_database
        response = requests.get(f"{server_url}/squirrels/1/extra/path")
        assert response.status_code == 404
    
    def it_returns_404_for_retrieve_after_deletion(reset_database):
        """Should return 404 when retrieving deleted squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Temporary", "size": "small"})
        requests.delete(f"{server_url}/squirrels/1")
        
        response = requests.get(f"{server_url}/squirrels/1")
        assert response.status_code == 404
    
    def it_returns_404_for_update_after_deletion(reset_database):
        """Should return 404 when updating deleted squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Temporary", "size": "small"})
        requests.delete(f"{server_url}/squirrels/1")
        
        response = requests.put(f"{server_url}/squirrels/1", data={"name": "Ghost", "size": "none"})
        assert response.status_code == 404
    
    def it_returns_404_for_double_deletion(reset_database):
        """Should return 404 when deleting already deleted squirrel"""
        server_url = reset_database
        requests.post(f"{server_url}/squirrels", data={"name": "Temporary", "size": "small"})
        requests.delete(f"{server_url}/squirrels/1")
        
        response = requests.delete(f"{server_url}/squirrels/1")
        assert response.status_code == 404
    
    def it_returns_404_with_text_plain_content_type(reset_database):
        """Should return text/plain content type for all 404s"""
        server_url = reset_database
        response = requests.get(f"{server_url}/invalid")
        assert response.headers["Content-Type"] == "text/plain"
    
    def it_returns_404_message_text_for_all_failures(reset_database):
        """Should return consistent '404 Not Found' message"""
        server_url = reset_database
        response = requests.get(f"{server_url}/invalid")
        assert response.text == "404 Not Found"


def describe_integration_workflows():
    """Test suite for complete workflows combining multiple operations"""
    
    def it_supports_complete_crud_cycle(reset_database):
        """Should support create, read, update, delete workflow"""
        server_url = reset_database
        # Create
        post_response = requests.post(f"{server_url}/squirrels", data={"name": "Lifecycle", "size": "small"})
        assert post_response.status_code == 201
        
        # Read
        get_response = requests.get(f"{server_url}/squirrels/1")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Lifecycle"
        
        # Update
        put_response = requests.put(f"{server_url}/squirrels/1", data={"name": "Updated", "size": "large"})
        assert put_response.status_code == 204
        
        # Verify update
        verify_response = requests.get(f"{server_url}/squirrels/1")
        assert verify_response.json()["name"] == "Updated"
        
        # Delete
        delete_response = requests.delete(f"{server_url}/squirrels/1")
        assert delete_response.status_code == 204
        
        # Verify deletion
        final_response = requests.get(f"{server_url}/squirrels/1")
        assert final_response.status_code == 404
    
    def it_maintains_data_consistency_across_operations(reset_database):
        """Should maintain consistent state through multiple operations"""
        server_url = reset_database
        # Create multiple squirrels
        requests.post(f"{server_url}/squirrels", data={"name": "A", "size": "small"})
        requests.post(f"{server_url}/squirrels", data={"name": "B", "size": "medium"})
        requests.post(f"{server_url}/squirrels", data={"name": "C", "size": "large"})
        
        # Verify count
        list_response = requests.get(f"{server_url}/squirrels")
        assert len(list_response.json()) == 3
        
        # Delete middle one
        requests.delete(f"{server_url}/squirrels/2")
        
        # Verify count updated
        list_response2 = requests.get(f"{server_url}/squirrels")
        assert len(list_response2.json()) == 2
        
        # Verify correct ones remain
        remaining = list_response2.json()
        names = [s["name"] for s in remaining]
        assert "A" in names
        assert "C" in names
        assert "B" not in names
