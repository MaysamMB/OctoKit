"""
Template storage and default-template seeding.

This is lifted from the original Tkinter Project Generator's
`TemplateManager` class almost unchanged - it never had any Tkinter
dependency to begin with (confirmed by full source inspection), so no
behavioral rewrite was needed here, only relocating it into the new
package layout. `DEFAULT_TEMPLATES` is copied verbatim from the original
script.
"""

from __future__ import annotations

from pathlib import Path

# ============================================================
# DEFAULT TEMPLATES (verbatim from the original script)
# ============================================================

DEFAULT_TEMPLATES = {

    "Basic Project": {
        "README.md": """# {{PROJECT_NAME}}

This project was created using Project Generator.

## Getting Started

Add your project documentation here.
""",

        ".gitignore": """__pycache__/
*.pyc
.env
.vscode/
.idea/
""",

        "src": {
            "main.py": """def main():
    print("Hello from {{PROJECT_NAME}}!")


if __name__ == "__main__":
    main()
"""
        }
    },

    "Python Project": {
        "README.md": """# {{PROJECT_NAME}}

Python project generated automatically.
""",

        "requirements.txt": """# Add your Python dependencies here
""",

        ".gitignore": """__pycache__/
*.py[cod]
.venv/
venv/
.env
.vscode/
.idea/
dist/
build/
*.egg-info/
""",

        "src": {
            "__init__.py": "",
            "main.py": """def main():
    print("Hello from {{PROJECT_NAME}}!")


if __name__ == "__main__":
    main()
"""
        },

        "tests": {
            "__init__.py": "",
            "test_main.py": """def test_example():
    assert True
"""
        }
    },

    "Web Project": {
        "README.md": """# {{PROJECT_NAME}}

Basic HTML/CSS/JavaScript web project.
""",

        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{PROJECT_NAME}}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>

    <h1>{{PROJECT_NAME}}</h1>

    <script src="js/script.js"></script>
</body>
</html>
""",

        "css": {
            "style.css": """body {
    font-family: Arial, sans-serif;
    margin: 40px;
}

h1 {
    margin-bottom: 20px;
}
"""
        },

        "js": {
            "script.js": """console.log("{{PROJECT_NAME}} loaded successfully.");
"""
        }
    },

    "Node.js": {
        "README.md": """# {{PROJECT_NAME}}

Node.js project generated automatically.
""",

        "package.json": """{
    "name": "{{PROJECT_NAME}}",
    "version": "1.0.0",
    "description": "",
    "main": "src/index.js",
    "scripts": {
        "start": "node src/index.js"
    },
    "dependencies": {}
}
""",

        ".gitignore": """node_modules/
.env
.vscode/
.idea/
""",

        "src": {
            "index.js": """console.log("{{PROJECT_NAME}} started.");
"""
        }
    },

    "React": {
        "README.md": """# {{PROJECT_NAME}}

React project generated automatically.
""",

        "package.json": """{
    "name": "{{PROJECT_NAME}}",
    "version": "1.0.0",
    "private": true,
    "dependencies": {
        "react": "^18.0.0",
        "react-dom": "^18.0.0"
    },
    "scripts": {
        "start": "react-scripts start",
        "build": "react-scripts build"
    }
}
""",

        ".gitignore": """node_modules/
build/
.env
.vscode/
.idea/
""",

        "public": {
            "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{PROJECT_NAME}}</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>
"""
        },

        "src": {
            "index.js": """import React from "react";
import { createRoot } from "react-dom/client";

function App() {
    return (
        <div>
            <h1>{{PROJECT_NAME}}</h1>
        </div>
    );
}

const root = createRoot(document.getElementById("root"));
root.render(<App />);
""",

            "App.js": """import React from "react";

function App() {
    return (
        <main>
            <h1>{{PROJECT_NAME}}</h1>
            <p>React project generated successfully.</p>
        </main>
    );
}

export default App;
"""
        }
    },

    "Flutter": {
        "README.md": """# {{PROJECT_NAME}}

Flutter project generated automatically.
""",

        "pubspec.yaml": """name: {{PROJECT_NAME}}
description: A Flutter project generated automatically.
publish_to: "none"

environment:
  sdk: ">=3.0.0 <4.0.0"

dependencies:
  flutter:
    sdk: flutter

flutter:
  uses-material-design: true
""",

        "lib": {
            "main.dart": """import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '{{PROJECT_NAME}}',
      home: Scaffold(
        appBar: AppBar(
          title: const Text('{{PROJECT_NAME}}'),
        ),
        body: const Center(
          child: Text(
            'Hello from {{PROJECT_NAME}}!',
          ),
        ),
      ),
    );
  }
}
"""
        }
    },

    "Java": {
        "README.md": """# {{PROJECT_NAME}}

Java project generated automatically.
""",

        ".gitignore": """*.class
target/
.idea/
.vscode/
""",

        "src": {
            "Main.java": """public class Main {

    public static void main(String[] args) {
        System.out.println("Hello from {{PROJECT_NAME}}!");
    }
}
"""
        }
    },

    "Spring Boot": {
        "README.md": """# {{PROJECT_NAME}}

Spring Boot project generated automatically.
""",

        "pom.xml": """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="
         http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">

    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>{{PROJECT_NAME}}</artifactId>
    <version>1.0.0</version>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.0</version>
        <relativePath/>
    </parent>

    <dependencies>

        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

    </dependencies>

</project>
""",

        "src": {
            "main": {
                "java": {
                    "com": {
                        "example": {
                            "Application.java": """package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
"""
                        }
                    }
                }
            }
        }
    },

    "C++": {
        "README.md": """# {{PROJECT_NAME}}

C++ project generated automatically.
""",

        ".gitignore": """build/
*.exe
*.o
.vscode/
.idea/
""",

        "src": {
            "main.cpp": """#include <iostream>

int main() {
    std::cout << "Hello from {{PROJECT_NAME}}!" << std::endl;

    return 0;
}
"""
        }
    },

    "C": {
        "README.md": """# {{PROJECT_NAME}}

C project generated automatically.
""",

        ".gitignore": """build/
*.exe
*.o
.vscode/
.idea/
""",

        "src": {
            "main.c": """#include <stdio.h>

int main(void) {
    printf("Hello from {{PROJECT_NAME}}!\\n");

    return 0;
}
"""
        }
    }
}


# ============================================================
# TEMPLATE MANAGER (unchanged logic from the original script)
# ============================================================

class TemplateManager:

    def __init__(self, templates_dir):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def create_default_templates(self):
        created = 0

        for template_name, structure in DEFAULT_TEMPLATES.items():
            template_path = self.templates_dir / template_name

            # Do not overwrite existing templates.
            template_path.mkdir(parents=True, exist_ok=True)

            created += self._create_structure(template_path, structure)

        return created

    def _create_structure(self, current_path, structure):
        created_files = 0

        for name, content in structure.items():
            path = current_path / name

            if isinstance(content, dict):
                path.mkdir(parents=True, exist_ok=True)
                created_files += self._create_structure(path, content)
            else:
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                    created_files += 1

        return created_files

    def get_templates(self):
        if not self.templates_dir.exists():
            return []

        templates = [
            folder.name
            for folder in self.templates_dir.iterdir()
            if folder.is_dir()
        ]

        return sorted(templates, key=str.lower)

    def get_template_path(self, template_name):
        return self.templates_dir / template_name

    def get_files(self, template_name):
        template_path = self.get_template_path(template_name)

        if not template_path.exists():
            return []

        files = []
        for path in template_path.rglob("*"):
            if path.is_file():
                files.append(path.relative_to(template_path))

        return sorted(files, key=lambda p: str(p).lower())

    def get_folders(self, template_name):
        template_path = self.get_template_path(template_name)

        if not template_path.exists():
            return []

        folders = set()
        for path in template_path.rglob("*"):
            if path.is_dir():
                folders.add(path.relative_to(template_path))

        return sorted(folders, key=lambda p: str(p).lower())

    def read_file(self, template_name, relative_file):
        template_path = self.get_template_path(template_name)
        file_path = template_path / relative_file
        return file_path.read_text(encoding="utf-8")

    def exists(self, template_name):
        return self.get_template_path(template_name).exists()
