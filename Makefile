APP_NAME = video-manipulator
SRC_DIR = src
ENTRY_POINT = $(SRC_DIR)/main.py
DIST_DIR = dist

.PHONY: all clean build run

all: build

build:
	@echo "Building standalone executable with PyInstaller..."
	pyinstaller --distpath $(DIST_DIR) --workpath build $(SRC_DIR)/main.spec
	@if [ -f "$(DIST_DIR)/$(APP_NAME)" ]; then \
		chmod +x $(DIST_DIR)/$(APP_NAME); \
	else \
		echo "Warning: Executable not found at $(DIST_DIR)/$(APP_NAME)"; \
	fi

run: build
	@if [ -f "$(DIST_DIR)/$(APP_NAME)" ]; then \
		./$(DIST_DIR)/$(APP_NAME); \
	else \
		echo "Error: Executable not found at $(DIST_DIR)/$(APP_NAME)"; \
		exit 1; \
	fi

clean:
	rm -rf build $(DIST_DIR)
