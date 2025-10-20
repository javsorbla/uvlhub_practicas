import pytest
from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile
from app.modules.notepad.services import NotepadService
from app.modules.auth.repositories import UserRepository
from app.modules.notepad.models import Notepad


@pytest.fixture(scope='module')
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Aqí creas el usuario (objeto en general) sobre el que vas a correr los tests (o si creas varios pues creas varias fixtures)
        user_test = User(email="user@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(user_id=user_test.id, name="Name", surname="Surname")
        db.session.add(profile)
        db.session.commit()

    yield test_client


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_list_empty_notepad_get(test_client):
    """
    Tests access to the empty notepad list via GET request.
    """
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    response = test_client.get("/notepad")
    assert response.status_code == 200, "The notepad page could not be accessed."
    assert b"You have no notepads." in response.data, "The expected content is not present on the page"

    logout(test_client)


def test_create_notepad(test_client):
    """
    Tests creation of notepad
    """
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    notepad_service = NotepadService() # Inicializa el servicio
    user_id = UserRepository().get_by_email("user@example.com").id  # Obtiene el id a partir del email (entiendo que habrá otra forma mejor pero bueno)
    previous_number = len(notepad_service.get_all_by_user(user_id))  # Obtiene el tamaño del array de notepads del usuario
    notepad_service.create(title="Prueba", body="prueba prueba prueba", user_id=user_id)
    assert len(notepad_service.get_all_by_user(user_id)) > previous_number, "Notepad could not be created"  # Esto comprueba que el array tras crear el notepad sea mayor

    logout(test_client)
    

def test_edit_notepad(test_client):
    """
    Tests creation of notepad
    """
    login_response = login(test_client, "user@example.com", "test1234")
    assert login_response.status_code == 200, "Login was unsuccessful."

    notepad_service = NotepadService()  # Inicializa el servicio
    user_id = UserRepository().get_by_email("user@example.com").id  # Obtiene el id a partir del email (entiendo que habrá otra forma mejor pero bueno)
    notepad = notepad_service.get_all_by_user(user_id)[0]
    new_notepad = Notepad(title="Prueba", body="hola hola", user_id=user_id)
    notepad_service.edit_notepad(notepad.id, new_notepad)
    after_edit = notepad_service.get_or_404(notepad.id)
    assert after_edit.body != notepad.body, "Notepad could not be edited"  # Esto comprueba que el array tras crear el notepad sea mayor

    logout(test_client)