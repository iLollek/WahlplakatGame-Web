#!/usr/bin/env python3
"""
Wahlsprüche Importer für WahlplakatGame Web-Version
Importiert Wahlsprüche aus JSON-Datei in die Datenbank
"""

import json
import sys
import os
from datetime import datetime
from database import DatabaseService

def import_wahlsprueche_from_json(json_filepath: str):
    """
    Importiert Wahlsprüche aus JSON-Datei
    
    Args:
        json_filepath: Pfad zur JSON-Datei
    
    Returns:
        Dictionary mit Import-Statistiken
    """
    
    # Prüfe ob Datei existiert
    if not os.path.exists(json_filepath):
        print(f"❌ Datei nicht gefunden: {json_filepath}")
        return None
    
    # Load JSON
    print(f"📖 Lade JSON-Datei: {json_filepath}")
    with open(json_filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Initialize Database
    print("🗄️  Verbinde mit Datenbank...")
    db = DatabaseService()
    
    # Statistics
    stats = {
        'total': 0,
        'created': 0,
        'skipped': 0,
        'errors': 0
    }
    
    # Process each Wahlspruch
    wahlsprueche = data.get('wahlsprueche', [])
    print(f"📊 Gefunden: {len(wahlsprueche)} Wahlsprüche\n")
    
    for item in wahlsprueche:
        stats['total'] += 1
        
        # Parse dictionary (key = Spruch, value = Metadata)
        for spruch, metadata in item.items():
            try:
                # Parse metadata: "Partei, Wahl, Datum, Quelle"
                parts = [p.strip() for p in metadata.split(',')]
                
                partei = parts[0] if len(parts) > 0 else None
                wahl = parts[1] if len(parts) > 1 else None
                datum_str = parts[2] if len(parts) > 2 else None
                quelle = parts[3] if len(parts) > 3 else None
                
                # Convert date string to date object
                datum = None
                if datum_str:
                    try:
                        datum = datetime.strptime(datum_str, "%d.%m.%Y").date()
                    except ValueError:
                        print(f"⚠️  Ungültiges Datum '{datum_str}' für: {spruch[:50]}...")
                
                # Create Wahlspruch
                success = db.create_new_wahlspruch(
                    text=spruch,
                    partei=partei,
                    wahl=wahl,
                    datum=datum,
                    quelle=quelle
                )
                
                if success:
                    stats['created'] += 1
                    print(f"✓ Erstellt: {spruch[:60]}...")
                else:
                    stats['skipped'] += 1
                    print(f"⊘ Übersprungen (existiert bereits): {spruch[:60]}...")
                    
            except Exception as e:
                stats['errors'] += 1
                print(f"✗ Fehler bei '{spruch[:50]}...': {str(e)}")
    
    # Print summary
    print("\n" + "="*70)
    print("IMPORT ZUSAMMENFASSUNG")
    print("="*70)
    print(f"Gesamt Einträge:    {stats['total']}")
    print(f"Neu erstellt:       {stats['created']}")
    print(f"Übersprungen:       {stats['skipped']}")
    print(f"Fehler:             {stats['errors']}")
    print("="*70)
    
    return stats


def main():
    """Main function"""
    print("=" * 70)
    print("🗳️  WahlplakatGame - Wahlsprüche Importer")
    print("=" * 70 + "\n")
    
    # Get JSON file path from command line or use default
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Try default locations
        possible_paths = [
            "../../Docs/wahlsprüche.json",
            "../Docs/wahlsprüche.json",
            "wahlsprüche.json"
        ]
        
        json_file = None
        for path in possible_paths:
            if os.path.exists(path):
                json_file = path
                break
        
        if not json_file:
            print("❌ Keine JSON-Datei gefunden!")
            print("\nVerwendung:")
            print(f"  python {sys.argv[0]} <pfad-zur-json-datei>")
            print("\nBeispiel:")
            print(f"  python {sys.argv[0]} ../../Docs/wahlsprüche.json")
            sys.exit(1)
    
    # Import
    result = import_wahlsprueche_from_json(json_file)
    
    if result:
        print("\n✅ Import abgeschlossen!")
        sys.exit(0)
    else:
        print("\n❌ Import fehlgeschlagen!")
        sys.exit(1)


if __name__ == "__main__":
    main()
