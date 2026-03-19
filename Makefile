VERSION_LOCAL := 0.0.0~local
PKG := jsonl-viewer_$(VERSION_LOCAL)_all

.PHONY: install build clean bump-patch bump-minor bump-major

install:
	./install.sh

build:
	rm -rf "$(PKG)" "$(PKG).deb"
	mkdir -p "$(PKG)/DEBIAN"
	mkdir -p "$(PKG)/usr/share/jsonl-viewer"
	mkdir -p "$(PKG)/usr/bin"
	mkdir -p "$(PKG)/usr/share/applications"
	mkdir -p "$(PKG)/usr/share/mime/packages"
	mkdir -p "$(PKG)/usr/share/icons/hicolor/scalable/apps"
	sed 's/^Version: VERSION$$/Version: $(VERSION_LOCAL)/' \
		debian/control > "$(PKG)/DEBIAN/control"
	cp debian/postinst "$(PKG)/DEBIAN/postinst"
	cp debian/prerm "$(PKG)/DEBIAN/prerm"
	cp jsonl-viewer.py "$(PKG)/usr/share/jsonl-viewer/jsonl-viewer.py"
	ln -s ../share/jsonl-viewer/jsonl-viewer.py "$(PKG)/usr/bin/jsonl-viewer"
	cp dev.jorj.jsonl-viewer.desktop "$(PKG)/usr/share/applications/"
	cp debian/jsonl-viewer.xml "$(PKG)/usr/share/mime/packages/"
	cp data/icons/hicolor/scalable/apps/dev.jorj.jsonl-viewer.svg \
		"$(PKG)/usr/share/icons/hicolor/scalable/apps/"
	cp data/icons/hicolor/scalable/apps/dev.jorj.jsonl-viewer-symbolic.svg \
		"$(PKG)/usr/share/icons/hicolor/scalable/apps/"
	dpkg-deb --root-owner-group --build "$(PKG)"
	@echo "Built $(PKG).deb"

clean:
	rm -rf jsonl-viewer_*_all jsonl-viewer_*_all.deb

bump-patch bump-minor bump-major:
	@current=$$(git describe --tags --abbrev=0 2>/dev/null || echo v0.0.0); \
	major=$$(echo $$current | sed 's/^v//' | cut -d. -f1); \
	minor=$$(echo $$current | sed 's/^v//' | cut -d. -f2); \
	patch=$$(echo $$current | sed 's/^v//' | cut -d. -f3); \
	case $@ in \
		bump-patch) patch=$$((patch + 1));; \
		bump-minor) minor=$$((minor + 1)); patch=0;; \
		bump-major) major=$$((major + 1)); minor=0; patch=0;; \
	esac; \
	new="v$$major.$$minor.$$patch"; \
	echo "$$current -> $$new"; \
	git tag "$$new" && \
	git push && git push origin "$$new"
