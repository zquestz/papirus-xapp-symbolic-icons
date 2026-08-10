PREFIX    ?= /usr
ICONDIR    = $(DESTDIR)$(PREFIX)/share/icons
USERICONDIR = $(HOME)/.local/share/icons

.PHONY: all icons install install-user uninstall uninstall-user

all: icons

# Regenerate mapping and icon set from the vendored submodules.
icons:
	python3 tools/build_mapping.py
	python3 tools/generate.py

# System-wide install: merge into the installed Papirus theme.
# Papirus-Dark and Papirus-Light pick these up through their existing
# symbolic-directory symlinks into Papirus.
install:
	mkdir -p $(ICONDIR)/Papirus
	cp -r icons/Papirus/. $(ICONDIR)/Papirus/
	-gtk-update-icon-cache -q -t -f $(ICONDIR)/Papirus

# Per-user install: icon lookup merges this with the system Papirus theme.
install-user:
	mkdir -p $(USERICONDIR)/Papirus
	cp -r icons/Papirus/. $(USERICONDIR)/Papirus/
	-gtk-update-icon-cache -q -t -f $(USERICONDIR)/Papirus

uninstall:
	find $(ICONDIR)/Papirus -name 'xsi-*.svg' -delete 2>/dev/null || true
	-gtk-update-icon-cache -q -t -f $(ICONDIR)/Papirus

uninstall-user:
	find $(USERICONDIR)/Papirus -name 'xsi-*.svg' -delete 2>/dev/null || true
	-gtk-update-icon-cache -q -t -f $(USERICONDIR)/Papirus
