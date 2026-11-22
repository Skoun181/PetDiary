"""Create a private, printable health record without external services."""
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def health_pdf(pet, records, attachments, checks, categories, created):
    result = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Meta", parent=styles["BodyText"], fontSize=9, leading=13,
                              textColor=colors.HexColor("#36554e"), spaceAfter=6))
    styles["Heading1"].textColor = colors.HexColor("#086653")
    styles["Heading2"].textColor = colors.HexColor("#086653")
    styles["BodyText"].spaceAfter = 6
    def para(value, style="BodyText"):
        clean = "".join(c for c in str(value) if ord(c) >= 32 or c in "\n\t")
        return Paragraph(escape(clean).replace("\n","<br/>"), styles[style])
    story = [para("PetDiary | Gesundheitsakte", "Heading1"), para(pet["name"],"Heading2"),
             para("Erstellt: " + created + " · Private Dokumentation, kein amtlicher Impfpass.", "Meta")]
    for key,label in (("species","Tierart"),("breed","Rasse"),("birth","Geburtsdatum"),("sex","Geschlecht"),
                      ("color","Fellfarbe"),("features","Merkmale"),("chip","Mikrochip"),("chip_date","Chipdatum"),
                      ("chip_location","Chipposition"),("tattoo","Tätowierung"),("tattoo_location","Position"),
                      ("owner","Halter"),("owner_contact","Kontakt"),("passport","Ausweisnummer"),
                      ("issuer","Ausgestellt durch"),("issued","Ausstellungsdatum")):
        if pet.get(key): story.append(para(label + ": " + str(pet[key])))
    story += [Spacer(1,12),para("Chronologische Gesundheitsakte","Heading1")]
    if not records: story.append(para("Noch keine Akteneinträge."))
    for row in records:
        story.append(para(row["day"] + " · " + categories.get(row["kind"],row["kind"]) + " · " + row["title"],"Heading2"))
        if row.get("parent_id"): story.append(para("Zusätzliches Präparat zum Akteneintrag Nr. " + str(row["parent_id"]), "Meta"))
        for key,label in (("vet","Praxis"),("product","Präparat"),("batch","Charge"),("valid_from","Gültig ab"),
                          ("valid_until","Gültig bis"),("weight","Gewicht (kg)"),("duration","Dauer (Tage)"),
                          ("dose_times","Uhrzeiten")):
            if row.get(key): story.append(para(label + ": " + str(row[key])))
        if row.get("dose"): story.append(para("Dokumentierte Menge: " + row["dose"] + " " + (row.get("dose_unit") or "")))
        if row.get("duration") and not row.get("dose_times"): story.append(para("Ohne feste Uhrzeit"))
        if row.get("due"): story.append(para("Erinnerung: " + row["due"] + (" (erledigt)" if row["done"] else " (offen)")))
        if row.get("notes"): story.append(para("Notizen: " + row["notes"]))
        if checks.get(row["id"]): story.append(para("Dokumentierte Gaben: " + str(checks[row["id"]])))
        for name in attachments.get(row["id"],[]): story.append(para("Anhang: " + name,"Meta"))
    story += [Spacer(1,12),para("Anhänge werden namentlich aufgeführt, nicht in das PDF eingebettet. Kostendaten und Zugangsdaten sind nicht Bestandteil dieser Gesundheitsakte.","Meta")]
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica",9)
        canvas.setFillColor(colors.HexColor("#36554e"))
        canvas.drawString(42,28,"PetDiary · Vertraulich")
        canvas.drawRightString(A4[0]-42,28,"Seite "+str(doc.page))
        canvas.restoreState()
    SimpleDocTemplate(result,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=48,
                      title="PetDiary Gesundheitsakte",author="PetDiary").build(story,onFirstPage=footer,onLaterPages=footer)
    result.seek(0)
    return result
