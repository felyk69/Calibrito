import os
import fitz
import ebookmeta

def test_pdf():
    file_path = "Ebooks/1_353588551352324928.pdf"
    print("Testing PDF:", file_path)
    try:
        with fitz.open(file_path) as doc:
            print("Metadata:", doc.metadata)
            if len(doc) > 0:
                print("First page text snippet:")
                text = doc.load_page(0).get_text("text").strip()
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                print("FIRST LINES:", lines[:5])
    except Exception as e:
        print("PDF Error:", e)

def test_mobi():
    file_path = "Ebooks/1_4900154614940172430.mobi"
    print("\nTesting MOBI:", file_path)
    try:
        meta = ebookmeta.get_metadata(file_path)
        print("Mobi Meta:", meta.title, meta.author_list)
    except Exception as e:
        print("Mobi Error:", type(e).__name__, str(e))

if __name__ == "__main__":
    test_pdf()
    test_mobi()
