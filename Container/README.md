# Container

Diese Ablage enthaelt die gemeinsame Container-Basis fuer spaetere ECCo-SP-Komponentenimages.

Aktueller Inhalt:

- `base-image/` als gemeinsames UBI-Minimal-Base-Image fuer Java-basierte ECCo-SP-Komponenten

Ziel der Struktur:

- gemeinsame Java-Laufzeit und Basiswerkzeuge nur einmal pflegen
- spaetere Komponentendockerfiles auf ein einheitliches Fundament setzen
- Shell- und Java-Anforderungen aus den bestehenden ECCo-SP-Deployments bereits im Basisimage abdecken