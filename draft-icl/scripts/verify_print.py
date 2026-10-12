"""Check saved XLSX settings; native conversion never proves Windows Excel."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as E
from zipfile import ZipFile
M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def verify(path,office=None):
    path=Path(path).resolve();expected=[]
    with ZipFile(path)as z:
        names=[n for n in z.namelist()if n.startswith('xl/worksheets/')and n.endswith('.xml')]
        if not names:raise ValueError('Workbook contains no worksheets.')
        for name in names:
            setup=E.fromstring(z.read(name)).find(M+'pageSetup')
            if setup is None or setup.get('orientation')!='landscape'or setup.get('paperSize')!='9':raise ValueError(f'{name}: expected explicit A4 landscape.')
        workbook=E.fromstring(z.read('xl/workbook.xml'));view=workbook.find(f'{M}bookViews/{M}workbookView')
        if view is None or view.get('activeTab','0')!='0':raise ValueError('Inspection sheet must be active on open.')
        areas=[n.text for n in workbook.findall(f'{M}definedNames/{M}definedName')if n.get('name')=='_xlnm.Print_Area'and n.get('localSheetId')=='0']
        if len(areas)!=1:raise ValueError('Main inspection print area must be one contiguous range.')
        sst=E.fromstring(z.read('xl/sharedStrings.xml'))if'xl/sharedStrings.xml'in z.namelist()else None
        main=E.fromstring(z.read('xl/worksheets/sheet1.xml'));setup=main.find(M+'pageSetup')
        if setup.get('fitToWidth')!='1'or setup.get('fitToHeight')!='1':raise ValueError('Inspection form must fit one page wide and tall.')
        fit=main.find(f'{M}sheetPr/{M}pageSetUpPr')
        if fit is None or fit.get('fitToPage')not in ['1','true']:raise ValueError('Inspection fitToPage is disabled.')
        def value(cell):
            if cell is None:return ''
            if cell.get('t')=='s':return ''.join(sst[int(cell.find(M+'v').text)].itertext())
            return ''.join(cell.itertext())
        for row in main.find(M+'sheetData'):
            cells={re.sub(r'\d','',c.get('r')):c for c in row}
            if re.fullmatch(r'[LBW]\d+',value(cells.get('B'))):expected.extend(value(cells.get(col))for col in ['B','C','E','G'])
        match=re.fullmatch(r"(?:'((?:[^']|'')+)'|([^'!]+))!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)",areas[0]or'')
        sheetname=workbook.find(M+'sheets')[0].get('name')
        if not match or(match[1].replace("''","'")if match[1]else match[2])!=sheetname:raise ValueError('Main print area points to an incorrect sheet/range.')
        def column(name):
            total=0
            for c in name:total=total*26+ord(c)-64
            return total
        used=[cell.get('r') for cell in main.iter(M+'c')if value(cell).strip()]
        lastrow=max(int(re.search(r'\d+',ref)[0])for ref in used)
        lastcol=max(20,max(column(re.match(r'[A-Z]+',ref)[0])for ref in used))
        if match[3]!='A'or int(match[4])!=1 or column(match[5])<lastcol or int(match[6])<lastrow:raise ValueError('Main print area omits check/header/footer content or sample columns.')
    report={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'file_page_setup_verified':True,
            'native_page_orientation_verified':False,'native_first_page_content_verified':False,'windows_excel_print_verified':False}
    if office:
        from pypdf import PdfReader
        with tempfile.TemporaryDirectory()as tmp:
            out=Path(tmp);profile=(out/'profile').as_uri()
            result=subprocess.run([office,'-env:UserInstallation='+profile,'--headless','--convert-to','pdf','--outdir',str(out),str(path)],capture_output=True,text=True,timeout=120)
            pdf=out/(path.stem+'.pdf')
            if result.returncode or not pdf.exists():raise ValueError('Native print conversion failed: '+result.stderr[-500:])
            pages=PdfReader(pdf).pages
            if not pages or any(abs(float(p.mediabox.width)-841.89)>2 or abs(float(p.mediabox.height)-595.28)>2 for p in pages):raise ValueError('Native print pages are not A4 landscape.')
            clean=lambda s:' '.join(s.split());text=clean(pages[0].extract_text())
            if any(clean(v)not in text for v in expected)or'VERIFIED BY'not in text.upper():raise ValueError('Native first page has missing check text or signing footer; inspect pagination.')
            preview=path.with_suffix('.print-preview.pdf');shutil.copy2(pdf,preview)
            report.update(native_page_orientation_verified=True,native_first_page_content_verified=True,native_engine=office,native_preview_file=preview.name)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('xlsx');parser.add_argument('--render',action='store_true');parser.add_argument('--office')
    args=parser.parse_args();office=(args.office or shutil.which('soffice'))if args.render else None
    if args.render and not office:parser.exit(1,'No spreadsheet application found; file flags alone do not verify rendered layout.\n')
    try:
        report=verify(args.xlsx,office);out=Path(args.xlsx).with_suffix('.print-settings.json');out.write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8');print(out)
    except (ValueError,ImportError,subprocess.TimeoutExpired)as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
