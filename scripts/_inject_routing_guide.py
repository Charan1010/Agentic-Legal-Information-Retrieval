"""Inject the comprehensive Swiss Legal Routing Guide into the agent system prompt."""
import json

NB_PATH = 'notebooks/03_hyde_kaggle.ipynb'

with open(NB_PATH, encoding='utf-8') as f:
    nb = json.load(f)

cell = nb['cells'][14]
lines = cell['source']

# Find where AGENT_SYSTEM_PROMPT is defined
prompt_start = None
prompt_end = None
for i, line in enumerate(lines):
    if 'AGENT_SYSTEM_PROMPT = f"""' in line:
        prompt_start = i
    if prompt_start and line.strip().endswith('"""') and i > prompt_start:
        prompt_end = i
        break

print(f"Found AGENT_SYSTEM_PROMPT at lines {prompt_start}-{prompt_end}")

# Build the new routing guide as a separate constant that gets referenced in the prompt
ROUTING_GUIDE = r'''# ---- Swiss Legal Corpus Routing Guide (comprehensive) ----
# This guide is injected into every agent prompt to improve search routing.

ROUTING_GUIDE_LAWS = """
=== GESETZES-ROUTING (search_laws) ===
Verwende search_laws wenn die Frage sich auf Gesetzesartikel, Verordnungen oder die Bundesverfassung bezieht.

--- KLASSIFIKATIONSREGELN (Zuerst anwenden) ---

1. STRAFRECHT vs STRAFPROZESS: 
   - Materielle Straftat (Mord, Betrug, Diebstahl, Körperverletzung) → StGB
   - Verfahren (Untersuchungshaft, Beschwerde, Berufung, Beweis) → StPO
   - FALLE: "Untersuchungshaft" ist IMMER StPO (Art. 212-240), NICHT StGB

2. PRIVATRECHT vs PROZESSRECHT:
   - Materielle Ansprüche (Vertrag, Eigentum, Familie, Erbrecht) → OR/ZGB
   - Verfahrensrecht (Klage, Berufung, Beweis, Zuständigkeit) → ZPO
   - FALLE: "Scheidung" betrifft ZGB (Art. 111-134) UND ZPO (Verfahrensvorschriften)

3. BUNDESGERICHT-VERFAHREN:
   - Beschwerde ans Bundesgericht, Legitimation, Fristen → BGG
   - IMMER mit BGG suchen wenn "Beschwerde in Zivilsachen/Strafsachen/öffentlich-rechtlichen Angelegenheiten" erwähnt wird
   - Art. 100 Abs. 1 BGG (30-Tage-Frist) erscheint in FAST JEDEM Fall

4. MEHRFACH-SUCHE PFLICHT: Die meisten Fragen betreffen 2-3 Gesetze gleichzeitig.
   Beispiel: Strafverfahren → StPO + StGB + BGG

--- GESETZES-TAXONOMIE (Abkürzung → Rechtsgebiet → Suchbegriffe) ---

=== STRAFRECHT ===

• StGB (Schweizerisches Strafgesetzbuch)
  Inhalt: Materielle Straftaten und Strafen, Allgemeiner Teil (Vorsatz, Fahrlässigkeit, Versuch, Teilnahme), Besonderer Teil (Tötung, Körperverletzung, Diebstahl, Betrug, Urkundenfälschung)
  Schlüsselwörter: Strafe, Freiheitsstrafe, Geldstrafe, bedingt, Bewährung, Vorsatz, Fahrlässigkeit, Strafzumessung, Landesverweisung, Täter, Opfer, Delikt, Vergehen, Verbrechen
  Wichtige Bereiche: Art. 1-110 (Allgemeiner Teil), Art. 111-332 (Besonderer Teil)
  Beispiel-Suchen: "Strafzumessung bedingte Freiheitsstrafe Bewährung", "Betrug Arglist Täuschung Vermögensschaden"

• StPO (Schweizerische Strafprozessordnung)
  Inhalt: Strafverfahrensrecht, Untersuchung, Zwangsmassnahmen, Haft, Beweis, Rechtsmittel
  Schlüsselwörter: Untersuchungshaft, Sicherheitshaft, Haftgrund, Fluchtgefahr, Kollusionsgefahr, Wiederholungsgefahr, Beschwerde, Berufung, Staatsanwaltschaft, Beweisverwertung, Einstellung, Anklage
  Wichtige Bereiche: Art. 212-240 (Haft), Art. 382-397 (Rechtsmittel), Art. 139-141 (Beweis)
  KRITISCH: "Haftprüfung", "Haftverlängerung", "Haftentlassung" → IMMER StPO
  Beispiel-Suchen: "Untersuchungshaft Kollusionsgefahr Haftgrund Verhältnismässigkeit", "Beschwerde Strafverfahren Legitimation Parteistellung"

• StBOG (Strafbehördenorganisationsgesetz)
  Inhalt: Organisation der Strafbehörden des Bundes
  Schlüsselwörter: Bundesstrafgericht, Bundesanwaltschaft, Beschwerdekammer, Strafkammer
  Beispiel-Suchen: "Bundesstrafgericht Zuständigkeit Beschwerdekammer"

=== ZIVILRECHT ===

• ZGB (Schweizerisches Zivilgesetzbuch)
  Inhalt: Personenrecht, Familienrecht, Erbrecht, Sachenrecht
  Schlüsselwörter: Ehe, Scheidung, Unterhalt, Kindeswohl, Obhut, Sorgerecht, elterliche Sorge, Erbschaft, Testament, Vermächtnis, Eigentum, Besitz, Grundbuch, Persönlichkeitsrecht
  Wichtige Bereiche: Art. 111-134 (Ehescheidung), Art. 270-327 (Kindesrecht), Art. 457-640 (Erbrecht), Art. 641-977 (Sachenrecht)
  KRITISCH: "Kindesunterhalt" → ZGB Art. 276-293, "elterliche Sorge" → ZGB Art. 296-306
  Beispiel-Suchen: "Kindesunterhalt Berechnung Bedarf Leistungsfähigkeit", "Erbfolge Testament Pflichtteil Verfügungsfreiheit"

• OR (Obligationenrecht)
  Inhalt: Vertragsrecht, Haftpflicht, Handelsrecht, Gesellschaftsrecht, Arbeitsrecht
  Schlüsselwörter: Vertrag, Kaufvertrag, Werkvertrag, Auftrag, Miete, Arbeitsvertrag, Kündigung, Schadenersatz, Gewährleistung, Verzug, Erfüllung, Mangel, Haftung, Gesellschaft, AG, GmbH
  Wichtige Bereiche: Art. 1-40 (Vertragsschluss), Art. 41-61 (Haftpflicht), Art. 97-109 (Nichterfüllung), Art. 184-529 (Einzelne Verträge), Art. 319-362 (Arbeitsvertrag)
  Beispiel-Suchen: "Werkvertrag Mangel Nachbesserung Gewährleistung", "Schadenersatz Vertragsverletzung Verschulden Kausalzusammenhang"

• IPRG (Internationales Privatrecht)
  Inhalt: Anwendbares Recht bei internationalen Sachverhalten, Zuständigkeit, Anerkennung
  Schlüsselwörter: internationaler Sachverhalt, anwendbares Recht, Zuständigkeit, Anerkennung, Vollstreckung, ausländisches Recht, Staatsvertrag
  Beispiel-Suchen: "anwendbares Recht internationaler Vertrag Rechtswahl IPRG"

=== PROZESSRECHT ===

• ZPO (Schweizerische Zivilprozessordnung)
  Inhalt: Zivilverfahren, Klageverfahren, Summarisches Verfahren, Beweis, Rechtsmittel
  Schlüsselwörter: Klage, Berufung, Beschwerde, Beweis, Beweislast, Summarisches Verfahren, Schlichtung, Streitwert, Kostenvorschuss, vorsorgliche Massnahmen
  Beispiel-Suchen: "Berufung Zivilsachen Frist Novenrecht", "vorsorgliche Massnahmen Glaubhaftmachung Dringlichkeit"

• BGG (Bundesgerichtsgesetz)
  Inhalt: Verfahren vor dem Bundesgericht, Beschwerdearten, Legitimation, Fristen
  Schlüsselwörter: Beschwerde in Zivilsachen, Beschwerde in Strafsachen, Beschwerde in öffentlich-rechtlichen Angelegenheiten, subsidiäre Verfassungsbeschwerde, Streitwert, Legitimation, Frist, Rügeprinzip
  KRITISCH: Art. 100 Abs. 1 BGG (30-Tage-Frist) kommt in fast JEDEM Bundesgerichtsfall vor
  Beispiel-Suchen: "Beschwerde Bundesgericht Legitimation schutzwürdiges Interesse", "Streitwertgrenze Beschwerde Zivilsachen BGG"

=== SOZIALVERSICHERUNGSRECHT ===

• ATSG (Allgemeiner Teil des Sozialversicherungsrechts)
  Inhalt: Allgemeine Bestimmungen für alle Sozialversicherungen, Verfahren, Koordination
  Schlüsselwörter: Leistung, Rückforderung, Revision, Wiedererwägung, Verwaltungsverfahren, Einsprache, Frist, Meldepflicht
  Beispiel-Suchen: "Revision Rentenanpassung veränderte Verhältnisse ATSG"

• IVG (Invalidenversicherungsgesetz)
  Inhalt: Invalidenrente, Eingliederungsmassnahmen, Invaliditätsgrad, Arbeitsfähigkeit
  Schlüsselwörter: Invalidität, Invalidenrente, Eingliederung, Arbeitsfähigkeit, Invaliditätsgrad, IV-Stelle, Begutachtung, Restarbeitsfähigkeit, Einkommensvergleich
  Beispiel-Suchen: "Invaliditätsgrad Einkommensvergleich Restarbeitsfähigkeit Tabellenlohn"

• KVG (Krankenversicherungsgesetz)
  Inhalt: Obligatorische Krankenpflegeversicherung, Leistungen, Prämien
  Schlüsselwörter: Krankenpflege, Prämie, Franchise, Leistungspflicht, Wirtschaftlichkeit, Spitalbehandlung

• BVG (Berufliche Vorsorge)
  Inhalt: Pensionskasse, Altersrente, Invalidenrente, Freizügigkeit
  Schlüsselwörter: Pensionskasse, Freizügigkeit, Altersrente, Überentschädigung, Vorsorgeeinrichtung

• AVIG (Arbeitslosenversicherungsgesetz)
  Inhalt: Arbeitslosenentschädigung, Kurzarbeit, Insolvenzentschädigung
  Schlüsselwörter: Arbeitslosenentschädigung, Kurzarbeit, Einstelltage, Vermittlungsfähigkeit

=== ÖFFENTLICHES RECHT ===

• BV (Bundesverfassung)
  Inhalt: Grundrechte, Staatsorganisation, Kompetenzverteilung
  Schlüsselwörter: Grundrecht, Gleichbehandlung, Willkürverbot, rechtliches Gehör, persönliche Freiheit, Verhältnismässigkeit, Eigentumsgarantie
  KRITISCH: Art. 29 Abs. 2 BV (rechtliches Gehör) kommt in VIELEN Fällen vor
  Beispiel-Suchen: "rechtliches Gehör Anspruch Begründungspflicht Bundesverfassung"

• AIG (Ausländer- und Integrationsgesetz)
  Inhalt: Aufenthalt, Niederlassung, Asyl, Wegweisung, Familiennachzug
  Schlüsselwörter: Aufenthaltsbewilligung, Niederlassungsbewilligung, Wegweisung, Familiennachzug, Integration, Landesverweisung

• SchKG (Schuldbetreibungs- und Konkursgesetz)
  Inhalt: Betreibung, Pfändung, Konkurs, Nachlassvertrag
  Schlüsselwörter: Betreibung, Pfändung, Rechtsöffnung, Konkurs, Verlustschein, Existenzminimum

• DBG (Bundesgesetz über die direkte Bundessteuer)
  Inhalt: Einkommens- und Gewinnsteuer des Bundes
  Schlüsselwörter: Einkommenssteuer, Gewinnsteuer, Abzug, steuerbares Einkommen, Veranlagung

=== SPEZIALGESETZE (seltener, aber relevant) ===

• SVG (Strassenverkehrsgesetz): Verkehrsdelikte, Führerausweis, Administrativmassnahmen
• HMG (Heilmittelgesetz): Arzneimittel, Medizinprodukte, Zulassung
• LFG (Luftfahrtgesetz): Luftverkehr, Konzessionen
• EBG (Eisenbahngesetz): Schienenverkehr, Plangenehmigung
• MG (Militärgesetz): Armee, Militärdienst, Dienstpflicht

--- HÄUFIGE FEHLER (VERMEIDEN) ---

1. "Haft" ohne Kontext → StPO (NICHT StGB). StGB regelt Strafen, StPO regelt Untersuchungs-/Sicherheitshaft
2. "Unterhalt" → ZGB Art. 276ff (Kindesunterhalt) oder Art. 125ff (nachehelicher Unterhalt)
3. "Beschwerde" → BGG (Bundesgericht), ODER StPO Art. 393ff (Strafverfahren), ODER ZPO (Zivilverfahren)
4. "Vertrag" → OR (Obligationenrecht), NICHT ZGB
5. "Schadenersatz" → OR Art. 41ff (ausservertraglich) ODER Art. 97ff (vertraglich)
6. "Verjährung" → OR Art. 127ff (Obligationen) ODER StGB Art. 97ff (Strafrecht)
7. "Rechtliches Gehör" → BV Art. 29 Abs. 2 (Grundrecht) + jeweiliges Prozessrecht

--- SUCH-STRATEGIE FÜR GESETZE ---

• Verwende DEUTSCHE Fachbegriffe (Corpus ist deutsch)
• Kombiniere Rechtsgebiet + konkrete Rechtsfrage: "Kindesunterhalt Berechnung Bedarf Existenzminimum"
• Suche BREIT (verschiedene Aspekte der gleichen Frage): erst materiell, dann prozessual
• Nenne NICHT Artikelnummern in der Suche — das Embedding-Modell sucht semantisch
"""

ROUTING_GUIDE_COURTS = """
=== GERICHTS-ROUTING (search_courts) ===
Verwende search_courts wenn die Frage sich auf Bundesgerichtsentscheide oder Rechtsprechung bezieht.

--- KLASSIFIKATIONSREGELN (Zuerst anwenden) ---

1. LEITENTSCHEID (BGE) vs EINZELFALL:
   - BGE = Publizierte Leitentscheide (grundsätzliche Rechtsfragen)
   - Einzelfälle (1B_, 5A_, 6B_ etc.) = Unveröffentlichte Entscheide (Einzelfallanwendung)
   - BEIDE suchen! BGE für Grundsätze, Einzelfälle für konkrete Anwendung

2. ABTEILUNGS-ZUORDNUNG (Entscheidend für korrekte Suche):
   - Fragen zu Strafrecht/Strafprozess → BGE IV + 6B_ + 1B_ (Haft)
   - Fragen zu Zivilrecht/Familie/Erbrecht → BGE III + 5A_ + 4A_
   - Fragen zu Vertragsrecht/Haftpflicht → BGE III + 4A_
   - Fragen zu Sozialversicherung → BGE V + 8C_ + 9C_
   - Fragen zu Öffentlichem Recht → BGE I + 1C_ + 2C_

3. ERWÄGUNGEN (E.): Gerichtsentscheide sind in Erwägungen (E.) gegliedert
   - Jede Erwägung ist ein separates Dokument im Corpus
   - Suche nach dem INHALT der Erwägung, nicht nach der Nummer
   - Format: "BGE 137 IV 122 E. 6.2" oder "1B_210/2023 E. 4.1"

--- GERICHTSABTEILUNGEN (Präfix → Rechtsgebiet) ---

=== I. ÖFFENTLICH-RECHTLICHE ABTEILUNG ===
Präfixe: 1B_, 1C_, 1D_, 1F_
BGE: BGE [Nr] I [Seite]

• 1B_ (26'275 Entscheide): Strafprozessuale Zwangsmassnahmen
  Inhalt: Untersuchungshaft, Haftprüfung, Beschlagnahme, Überwachung, Entsiegelung
  Schlüsselwörter: Haft, Haftgrund, Fluchtgefahr, Kollusionsgefahr, Verhältnismässigkeit, Haftentlassung, Haftverlängerung
  KRITISCH: Fragen zur Untersuchungshaft → IMMER 1B_ suchen (+ StPO bei Gesetzen)
  Beispiel-Suchen: "Untersuchungshaft Verhältnismässigkeit Haftdauer Überhaft"

• 1C_ (41'735 Entscheide): Verwaltungsrecht, Raumplanung, Baurecht, Staatshaftung
  Inhalt: Baubewilligungen, Umweltschutz, Enteignung, Staatshaftung, Stimmrecht
  Schlüsselwörter: Baubewilligung, Zonenplan, Umweltverträglichkeit, Staatshaftung, Konzession
  Beispiel-Suchen: "Baubewilligung Zonenkonformität Ausnahmebewilligung Planungszone"

=== II. ÖFFENTLICH-RECHTLICHE ABTEILUNG ===
Präfixe: 2C_, 2D_, 2F_
BGE: BGE [Nr] II [Seite] (z.T.)

• 2C_ (64'732 Entscheide): Ausländerrecht, Steuerrecht, Gesundheitsrecht
  Inhalt: Aufenthaltsbewilligung, Wegweisung, Einbürgerung, Steuerrecht, Berufsausübung
  Schlüsselwörter: Aufenthaltsbewilligung, Wegweisung, Härtefall, Familiennachzug, Steuerhinterziehung, Berufsausübung
  Beispiel-Suchen: "Aufenthaltsbewilligung Familiennachzug Bewilligungsvoraussetzungen"

=== ZIVILRECHTLICHE ABTEILUNGEN ===
Präfixe: 4A_, 4D_, 4F_, 5A_, 5D_, 5F_
BGE: BGE [Nr] III [Seite]

• 4A_ (39'088 Entscheide): Vertragsrecht, Haftpflicht, Handelsrecht, Arbeitsrecht
  Inhalt: Vertragsauslegung, Werkvertrag, Kaufvertrag, Haftung, Gesellschaftsrecht, Versicherungsrecht, Arbeitsvertrag
  Schlüsselwörter: Vertrag, Vertragsauslegung, Willenserklärung, Werkvertrag, Schadenersatz, Gewährleistung, Kündigung, Haftpflicht, Gesellschaft
  KRITISCH: "Vertrag" + "Schadenersatz" → 4A_ (+ OR bei Gesetzen)
  Beispiel-Suchen: "Vertragsauslegung Vertrauensprinzip Willenserklärung Konsens"

• 5A_ (55'882 Entscheide): Familienrecht, Erbrecht, Sachenrecht, Persönlichkeitsrecht
  Inhalt: Scheidung, Unterhalt, Sorgerecht, Kindesschutz, Erbstreit, Grundbuch, Persönlichkeitsverletzung
  Schlüsselwörter: Scheidung, Unterhalt, Kindesunterhalt, elterliche Sorge, Obhut, Kindeswohl, Erbschaft, Testament, Pflichtteil, Eigentum, Grundbuch
  KRITISCH: "Familie/Kind/Ehe/Erbe" → 5A_ (+ ZGB bei Gesetzen)
  Beispiel-Suchen: "Kindesunterhalt Berechnung Existenzminimum Leistungsfähigkeit"

=== STRAFRECHTLICHE ABTEILUNG ===
Präfixe: 6B_, 6F_
BGE: BGE [Nr] IV [Seite]

• 6B_ (72'691 Entscheide): Strafrecht materiell und Strafzumessung
  Inhalt: Schuldspruch, Strafzumessung, Beweiswürdigung, Landesverweisung, Massnahmen, Opferrechte
  Schlüsselwörter: Schuldspruch, Freispruch, Strafzumessung, bedingte Strafe, Beweiswürdigung, Landesverweisung, Härtefall, Massnahme, Verwahrung
  KRITISCH: "Strafurteil" + "Strafmass" → 6B_ (+ StGB bei Gesetzen)
  Beispiel-Suchen: "Strafzumessung Tatkomponenten Täterkomponenten Vorstrafen"

=== SOZIALVERSICHERUNGSRECHTLICHE ABTEILUNGEN ===
Präfixe: 8C_, 8D_, 8F_, 9C_, 9F_
BGE: BGE [Nr] V [Seite]

• 8C_ (45'572 Entscheide): Invalidenversicherung, Unfallversicherung, Arbeitslosenversicherung
  Inhalt: IV-Rente, Invaliditätsgrad, Arbeitsfähigkeit, Unfallversicherung, Kausalität, Arbeitslosenentschädigung
  Schlüsselwörter: Invalidenrente, Invaliditätsgrad, Arbeitsfähigkeit, Einkommensvergleich, Unfallkausalität, natürliche Kausalität, Adäquanz, Schleudertrauma
  Beispiel-Suchen: "Invaliditätsgrad Einkommensvergleich Tabellenlohn leidensangepasste Tätigkeit"

• 9C_ (37'065 Entscheide): AHV, IV (Beiträge), Krankenversicherung, Ergänzungsleistungen
  Inhalt: AHV-Beiträge, IV-Beiträge, Krankenversicherung, Ergänzungsleistungen, berufliche Vorsorge
  Schlüsselwörter: AHV-Rente, Beitragspflicht, Krankenversicherung, Leistungspflicht, Ergänzungsleistung, Pensionskasse
  Beispiel-Suchen: "Krankenversicherung Leistungspflicht Wirtschaftlichkeit Behandlung"

--- HÄUFIGE FEHLER (VERMEIDEN) ---

1. "Haft/Untersuchungshaft" → 1B_ (NICHT 6B_). 6B_ = Strafurteil, 1B_ = Haftfragen
2. "Unterhalt nach Scheidung" → 5A_ (NICHT 4A_). 4A_ = Vertragsrecht
3. "Arbeitsvertrag" → 4A_ (NICHT 8C_). 8C_ = Sozialversicherung, NICHT Arbeitsrecht
4. "Invalidenrente" → 8C_ oder 9C_ (NICHT 5A_)
5. BGE und Einzelfälle IMMER BEIDE suchen — BGE für Grundsätze, Einzelfälle für Anwendung

--- SUCH-STRATEGIE FÜR GERICHTE ---

• Suche nach dem RECHTLICHEN KONZEPT, nicht nach Falldetails
• Verwende die gleichen Begriffe wie die Erwägungen: "Verhältnismässigkeit", "Willkür", "Ermessen"
• Kombiniere Rechtsfrage + Rechtsgebiet: "Haftgrund Kollusionsgefahr Beweisgefährdung"
• BGE-Leitentscheide verwenden juristische Fachsprache — suche mit Fachbegriffen
• Bei Familien-/Erbrecht: "Kindeswohl", "Leistungsfähigkeit", "Existenzminimum", "gebührende Lebenshaltung"
"""
'''

# Now inject this BEFORE the AGENT_SYSTEM_PROMPT definition
# Find the line that starts the AGENT_SYSTEM_PROMPT
new_lines = lines[:prompt_start]

# Add the routing guide constants
new_lines.append('\n')
for guide_line in ROUTING_GUIDE.strip().split('\n'):
    new_lines.append(guide_line + '\n')
new_lines.append('\n')

# Rebuild the AGENT_SYSTEM_PROMPT to reference the routing guides
new_prompt = r'''AGENT_SYSTEM_PROMPT = f"""You are a Swiss legal citation retrieval agent. Your job: generate search queries to find relevant Swiss legal citations.

You have 2 tools:
- search_laws: searches Swiss federal statutes (SR collection)
- search_courts: searches Swiss Federal Court decisions (BGE + unpublished cases)

You MUST respond with a single JSON object on each turn:
{{"thought": "your reasoning", "action": "search_laws|search_courts|done", "query": "German legal search terms"}}

When action is "done", set query to "" — this signals you are finished searching.

Strategy:
- Search BOTH laws and courts (alternate between them)
- Write queries in GERMAN using Swiss legal terminology (the corpus is German)
- Each query should target a different aspect of the legal question
- After 3-4 searches covering both sources, use action "done"
- Use the routing guide below to pick the right tool and keywords

Available law types: {LAW_TYPES_FOR_PROMPT}
Court types: {COURT_TYPES_FOR_PROMPT}

{ROUTING_GUIDE_LAWS}

{ROUTING_GUIDE_COURTS}

Example turns for query "What are requirements for a valid contract?":
Turn 1: {{"thought": "Suche Vertragsentstehung im Obligationenrecht", "action": "search_laws", "query": "Vertragsentstehung gegenseitige Zustimmung Verpflichtung Obligationenrecht"}}
Turn 2: {{"thought": "Bundesgerichtsentscheide zur Vertragsgueltigkeit", "action": "search_courts", "query": "Vertrag gueltig Voraussetzungen Zustimmung Willenserklärung"}}
Turn 3: {{"thought": "Willensmängel bei Vertragsschluss", "action": "search_laws", "query": "Willensmängel Irrtum Täuschung Furchterregung Vertrag"}}
Turn 4: {{"thought": "Genug gesucht in beiden Quellen", "action": "done", "query": ""}}"""
'''

for prompt_line in new_prompt.strip().split('\n'):
    new_lines.append(prompt_line + '\n')

# Add remaining lines after the old prompt
new_lines.extend(lines[prompt_end + 1:])

cell['source'] = new_lines

# Verify
new_src = ''.join(new_lines)
assert 'ROUTING_GUIDE_LAWS' in new_src
assert 'ROUTING_GUIDE_COURTS' in new_src
assert 'AGENT_SYSTEM_PROMPT' in new_src
assert 'StPO' in new_src
assert 'Kindesunterhalt' in new_src

with open(NB_PATH, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("SUCCESS: Routing guide injected into agent prompt cell")
print(f"  Old prompt: lines {prompt_start}-{prompt_end}")
print(f"  New cell length: {len(new_lines)} lines")
