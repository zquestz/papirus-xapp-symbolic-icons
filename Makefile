PREFIX    ?= /usr
ICONDIR    = $(DESTDIR)$(PREFIX)/share/icons
USERICONDIR = $(HOME)/.local/share/icons

# Papirus-Dark and Papirus-Light reach our icons through symlinks into
# Papirus, but each variant has its own icon-theme.cache; all three must be
# refreshed or the variants keep serving stale lookups that miss our icons.
VARIANTS = Papirus Papirus-Dark Papirus-Light

.PHONY: all icons preview install install-user uninstall uninstall-user

all: icons

# Regenerate mapping and icon set from the vendored submodules.
icons:
	python3 tools/build_mapping.py
	python3 tools/generate.py

# Re-render preview.png (needs python-pillow and librsvg).
preview:
	python3 tools/preview.py

# System-wide install: merge into the installed Papirus theme.
# Papirus-Dark and Papirus-Light pick these up through their existing
# symbolic-directory symlinks into Papirus.
install:
	mkdir -p $(ICONDIR)/Papirus
	cp -r icons/Papirus/. $(ICONDIR)/Papirus/
	for t in $(VARIANTS); do \
		test -f $(ICONDIR)/$$t/index.theme && gtk-update-icon-cache -q -t -f $(ICONDIR)/$$t || :; \
	done

# Per-user install: icon lookup merges this with the system Papirus theme.
install-user:
	mkdir -p $(USERICONDIR)/Papirus
	cp -r icons/Papirus/. $(USERICONDIR)/Papirus/
	for t in $(VARIANTS); do \
		test -f $(USERICONDIR)/$$t/index.theme && gtk-update-icon-cache -q -t -f $(USERICONDIR)/$$t || :; \
	done

uninstall:
	find $(ICONDIR)/Papirus -name 'xsi-*.svg' -delete 2>/dev/null || true
	for t in $(VARIANTS); do \
		test -f $(ICONDIR)/$$t/index.theme && gtk-update-icon-cache -q -t -f $(ICONDIR)/$$t || :; \
	done

uninstall-user:
	find $(USERICONDIR)/Papirus -name 'xsi-*.svg' -delete 2>/dev/null || true
	for t in $(VARIANTS); do \
		test -f $(USERICONDIR)/$$t/index.theme && gtk-update-icon-cache -q -t -f $(USERICONDIR)/$$t || :; \
	done
