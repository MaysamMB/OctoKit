import pytest

from core.exceptions import InvalidProjectNameError, ProjectAlreadyExistsError, ToolkitError
from features.project_generator.service import ProjectGeneratorService
from features.project_generator.template_manager import TemplateManager


@pytest.fixture
def service(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()
    return ProjectGeneratorService(manager)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_empty_name_rejected(service):
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name("")


@pytest.mark.parametrize("bad_char", list('<>:"/\\|?*'))
def test_invalid_windows_characters_rejected(service, bad_char):
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name(f"My{bad_char}Project")


def test_dot_and_dotdot_rejected(service):
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name(".")
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name("..")


@pytest.mark.parametrize("name", ["CON", "con", "PRN", "NUL", "COM1", "LPT9", "con.txt", "COM1.backup"])
def test_reserved_windows_names_rejected(service, name):
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name(name)


def test_trailing_dot_or_space_rejected(service):
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name("MyProject.")
    with pytest.raises(InvalidProjectNameError):
        service.validate_project_name("MyProject ")


def test_valid_name_passes(service):
    service.validate_project_name("MyProject_123-final")  # must not raise


def test_missing_location_rejected(service, tmp_path):
    with pytest.raises(ToolkitError):
        service.validate_location(tmp_path / "does_not_exist")


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


def test_preview_lists_files_and_folders(service):
    preview = service.preview("Python Project", "MyApp")
    assert preview.file_count > 0
    assert preview.folder_count > 0
    assert "MyApp/" in preview.tree_text


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_generate_creates_project_with_variables_replaced(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()

    result = service.generate("Basic Project", "MyApp", location)

    assert result.project_path == location / "MyApp"
    assert (location / "MyApp" / "README.md").exists()
    readme = (location / "MyApp" / "README.md").read_text(encoding="utf-8")
    assert "MyApp" in readme
    assert "{{PROJECT_NAME}}" not in readme

    config = (location / "MyApp" / "config.json").read_text(encoding="utf-8")
    assert '"project_name": "MyApp"' in config


def test_generate_reports_created_files_and_folders(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()
    result = service.generate("Python Project", "MyApp", location)

    assert any(str(f) == "src/main.py" for f in result.files_created)
    assert any(str(fo) == "src" for fo in result.folders_created)


def test_generate_raises_on_existing_project_without_force(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()
    (location / "MyApp").mkdir()

    with pytest.raises(ProjectAlreadyExistsError):
        service.generate("Basic Project", "MyApp", location)

    # Nothing should have been written into the existing folder.
    assert list((location / "MyApp").iterdir()) == []


def test_generate_reports_conflicts_in_error_details(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()
    existing = location / "MyApp"
    existing.mkdir()
    (existing / "README.md").write_text("pre-existing content", encoding="utf-8")

    with pytest.raises(ProjectAlreadyExistsError) as exc_info:
        service.generate("Basic Project", "MyApp", location)

    assert "README.md" in exc_info.value.technical_details
    # Must not have touched the pre-existing file.
    assert existing.joinpath("README.md").read_text(encoding="utf-8") == "pre-existing content"


def test_generate_with_force_overwrite_proceeds(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()
    existing = location / "MyApp"
    existing.mkdir()
    (existing / "README.md").write_text("old content", encoding="utf-8")

    result = service.generate("Basic Project", "MyApp", location, force_overwrite=True)

    assert "MyApp" in str(result.project_path)
    new_content = (existing / "README.md").read_text(encoding="utf-8")
    assert "old content" not in new_content
    assert str(existing / "README.md").endswith("README.md")


def test_generate_rejects_invalid_name_before_touching_disk(service, tmp_path):
    location = tmp_path / "projects"
    location.mkdir()
    with pytest.raises(InvalidProjectNameError):
        service.generate("Basic Project", "CON", location)
    assert list(location.iterdir()) == []


def test_generate_with_missing_template_raises(service, tmp_path):
    from core.exceptions import TemplateNotFoundError

    location = tmp_path / "projects"
    location.mkdir()
    with pytest.raises(TemplateNotFoundError):
        service.generate("Nonexistent Template", "MyApp", location)


def test_binary_file_is_copied_without_variable_replacement(service, tmp_path):
    # Add a "binary" file to a template and confirm it round-trips via the
    # UnicodeDecodeError fallback path rather than crashing.
    template_path = service.template_manager.get_template_path("Basic Project")
    binary_path = template_path / "icon.bin"
    binary_path.write_bytes(bytes([0xFF, 0xFE, 0x00, 0x01, 0x02]))

    location = tmp_path / "projects"
    location.mkdir()
    result = service.generate("Basic Project", "MyApp", location)

    dest = location / "MyApp" / "icon.bin"
    assert dest.exists()
    assert dest.read_bytes() == bytes([0xFF, 0xFE, 0x00, 0x01, 0x02])
