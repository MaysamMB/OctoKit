from features.project_generator.template_manager import DEFAULT_TEMPLATES, TemplateManager


def test_creates_templates_dir(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    assert (tmp_path / "templates").exists()


def test_create_default_templates_creates_all(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()
    templates = manager.get_templates()
    for name in DEFAULT_TEMPLATES:
        assert name in templates


def test_default_templates_never_overwritten(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()

    readme = manager.get_template_path("Basic Project") / "README.md"
    readme.write_text("MY CUSTOM CONTENT", encoding="utf-8")

    manager.create_default_templates()  # run again, e.g. on next app launch
    assert readme.read_text(encoding="utf-8") == "MY CUSTOM CONTENT"


def test_get_files_and_folders(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()

    files = manager.get_files("Python Project")
    folders = manager.get_folders("Python Project")

    assert any(str(f) == "src/main.py" for f in files)
    assert any(str(f) == "tests/test_main.py" for f in files)
    assert any(str(fo) == "src" for fo in folders)


def test_exists(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()
    assert manager.exists("React") is True
    assert manager.exists("Nonexistent Template") is False


def test_read_file_contains_variable_placeholder(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()
    content = manager.read_file("Basic Project", "README.md")
    assert "{{PROJECT_NAME}}" in content


def test_custom_user_template_is_preserved_and_listed(tmp_path):
    manager = TemplateManager(tmp_path / "templates")
    manager.create_default_templates()

    custom_dir = manager.get_template_path("MyCustomTemplate")
    custom_dir.mkdir()
    (custom_dir / "hello.txt").write_text("hi", encoding="utf-8")

    manager.create_default_templates()  # must not disturb the custom template
    assert "MyCustomTemplate" in manager.get_templates()
    assert (custom_dir / "hello.txt").read_text(encoding="utf-8") == "hi"
