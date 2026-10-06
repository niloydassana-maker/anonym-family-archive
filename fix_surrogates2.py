# -*- coding: utf-8 -*-
"""Replace lone-surrogate emoji with real chars; report literal astral escapes."""
import re

S1A = 'ÞÙ'
S1B = 'ÞØ'
S1C = 'Þ¤'
R1A = '¹'
R1B = '¨'
R1C = 'º'
print('search chars:', [hex(ord(x)) for x in S1A + S1B + S1C])
print('repl chars:', [hex(ord(x)) for x in R1A + R1B + R1C])
