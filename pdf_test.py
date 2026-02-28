#!/usr/bin/env python
# -*- coding: utf8 -*-

from fpdf import FPDF

pdf = FPDF()
pdf.add_page()

# Add a DejaVu Unicode font (uses UTF-8)
# Supports more than 200 languages. For a coverage status see:
# http://dejavu.svn.sourceforge.net/viewvc/dejavu/trunk/dejavu-fonts/langcover.txt
pdf.add_font('DejaVu', '', r'font/DejaVuSansCondensed.ttf')
pdf.set_font('DejaVu', '', 14)

text = u"""
English: Hello World Greek: Γειά σου κόσμς 999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
Polish: Witaj świecie
Portuguese: Olá mundo
Russian: Здравствуй, Мир
Vietnamese: Xin chào thế giới
Arabic: مرحبا العالم
Hebrew: שלום עולם
"""

pdf.write( text="No margin -------------------------------------------")
pdf.ln(10)
pdf.set_left_margin(10)
pdf.write(text="gggggggggggggggggggggggggggggggggggggg")
pdf.ln(10)
pdf.set_left_margin(5)
pdf.write(text="1.DDdhfddhjhklgljhjhjhllllllllllllllllllll")

for txt in text.split('\n'):
    pdf.set_left_margin(20)
    pdf.write(text=txt)
    pdf.ln(8)
# Select a standard font (uses windows-1252)
pdf.set_font('Arial', '', 14)
pdf.ln(10)
pdf.write(text='This is standard built-in font')

pdf.output("unicode.pdf")
