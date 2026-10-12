"""Compact only the checkpoint grid; preserve the company form around it."""
import copy
import re
from lxml import etree as E
M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def compact(sheet,layout,checks,styles):
    groups=layout['groups'];counts={g:sum(c.get('group','main')==g for c in checks) for g in groups}
    data=sheet.find(M+'sheetData');rows={int(r.get('r')):r for r in data}
    ends={g:max(rr) for g,rr in groups.items()};starts={min(rr):g for g,rr in groups.items()}
    covered={r for rr in groups.values() for r in rr};headers=layout.get('group_headers',{})
    header_groups={r:g for g,r in headers.items()};mapping={};slots={g:[]for g in groups};newrows=[];newnum=0
    total=max(rows);prototypes={g:copy.deepcopy(rows[min(rr)])for g,rr in groups.items()}
    for oldnum in range(1,total+1):
        if oldnum in starts:
            g=starts[oldnum]
            for index in range(counts[g]):
                newnum+=1;slots[g].append(newnum);row=copy.deepcopy(prototypes[g]);row.set('r',str(newnum));row.set('ht','24');row.set('customHeight','1')
                for cell in row:
                    cell.set('r',re.sub(r'\d+$',str(newnum),cell.get('r')))
                    for node in list(cell):cell.remove(node)
                    cell.attrib.pop('t',None)
                newrows.append(row)
            mapping[oldnum]=slots[g][0] if slots[g]else None
        elif oldnum in covered:mapping[oldnum]=None
        elif oldnum in header_groups and not counts[header_groups[oldnum]]:mapping[oldnum]=None
        else:
            newnum+=1;mapping[oldnum]=newnum
            if oldnum in rows:
                row=copy.deepcopy(rows[oldnum]);row.set('r',str(newnum))
                for cell in row:cell.set('r',re.sub(r'\d+$',str(newnum),cell.get('r')))
                newrows.append(row)
    data[:]=newrows
    def remap(ref):
        nums=[int(n)for n in re.findall(r'\d+',ref)]
        if any(mapping.get(n) is None for n in nums):return None
        return re.sub(r'\d+',lambda m:str(mapping[int(m[0])]),ref)
    merges=sheet.find(M+'mergeCells');bodymerges={g:[]for g in groups}
    for node in list(merges):
        ref=node.get('ref');nums=[int(n)for n in re.findall(r'\d+',ref)]
        owner=next((g for g,rr in groups.items() if nums and all(n in rr for n in nums)),None)
        if owner:
            if all(n==min(groups[owner]) for n in nums):bodymerges[owner].append(ref)
            merges.remove(node)
        else:
            updated=remap(ref)
            if updated:node.set('ref',updated)
            else:merges.remove(node)
    for g,rr in slots.items():
        for row in rr:
            for ref in bodymerges[g]:E.SubElement(merges,M+'mergeCell',ref=re.sub(r'\d+',str(row),ref))
    merges.set('count',str(len(merges)))
    for node in sheet.findall(M+'rowBreaks')+sheet.findall(M+'colBreaks'):sheet.remove(node)
    sheet.find(M+'dimension').set('ref',f'A1:T{newnum}')
    fonts=styles.find(M+'fonts');font=E.Element(M+'font');E.SubElement(font,M+'sz',val='10');E.SubElement(font,M+'name',val='Arial');E.SubElement(font,M+'family',val='2');fontid=str(len(fonts));fonts.append(font);fonts.set('count',str(len(fonts)))
    xfs=styles.find(M+'cellXfs');cache={}
    for row in data:
        if int(row.get('r'))not in [r for rr in slots.values()for r in rr]:continue
        for cell in row:
            col=re.match(r'[A-Z]+',cell.get('r'))[0];key=(cell.get('s','0'),col)
            if key not in cache:
                xf=copy.deepcopy(xfs[int(key[0])]);xf.set('fontId',fontid);xf.set('applyFont','1');xf.set('applyAlignment','1');align=xf.find(M+'alignment')
                if align is None:align=E.SubElement(xf,M+'alignment')
                align.attrib.update({'vertical':'center','horizontal':'left'if col=='C'else'center','wrapText':'1'if col=='C'else'0','shrinkToFit':'0'})
                cache[key]=str(len(xfs));xfs.append(xf)
            cell.set('s',cache[key])
    xfs.set('count',str(len(xfs)))
    updated=copy.deepcopy(layout);updated['groups']=slots;updated['clear_rows']=[r for rr in slots.values()for r in rr]
    updated['clear_cells']=[v for ref in layout['clear_cells'] if (v:=remap(ref))]
    updated['fixed_cells']={v:value for ref,value in layout['fixed_cells'].items()if(v:=remap(ref))}
    updated['metadata']={remap(ref):field for ref,field in layout['metadata'].items()}
    updated['drawing']['row']=mapping[layout['drawing']['row']+1]-1
    last=mapping.get(layout.get('print_last_row',total),newnum)
    return updated,last


def print_setup(parts,layout,last):
    for index,name in enumerate([layout['sheet'],layout['history']]):
        root=E.fromstring(parts[name]);pr=root.find(M+'sheetPr')
        if pr is None:pr=E.Element(M+'sheetPr');root.insert(0,pr)
        fit=pr.find(M+'pageSetUpPr')
        if fit is None:fit=E.SubElement(pr,M+'pageSetUpPr')
        fit.set('fitToPage','true')
        setup=root.find(M+'pageSetup')
        if setup is None:
            setup=E.Element(M+'pageSetup');margins=root.find(M+'pageMargins');root.insert(list(root).index(margins)+1,setup)
        setup.attrib.pop(R+'id',None)
        setup.attrib.update({'paperSize':'9','orientation':'landscape','fitToWidth':'1','fitToHeight':'1'if index==0 else'0','usePrinterDefaults':'false','scale':'100'})
        for view in root.findall(f'{M}sheetViews/{M}sheetView'):view.set('tabSelected','1'if index==0 else'0')
        parts[name]=E.tostring(root,encoding='utf-8',xml_declaration=True)
    for name in list(parts):
        if name.startswith('xl/printerSettings/'):del parts[name]
        elif name.startswith('xl/worksheets/_rels/')and name.endswith('.rels'):
            rels=E.fromstring(parts[name])
            for rel in list(rels):
                if rel.get('Type','').endswith('/printerSettings'):rels.remove(rel)
            parts[name]=E.tostring(rels,encoding='utf-8',xml_declaration=True)
    types=E.fromstring(parts['[Content_Types].xml'])
    for item in list(types):
        if 'printerSettings'in item.get('ContentType','')or item.get('PartName','').startswith('/xl/printerSettings/'):types.remove(item)
    parts['[Content_Types].xml']=E.tostring(types,encoding='utf-8',xml_declaration=True)
    book=E.fromstring(parts['xl/workbook.xml'])
    for view in book.findall(f'{M}bookViews/{M}workbookView'):view.attrib.update({'activeTab':'0','firstSheet':'0'})
    names=book.find(M+'definedNames')
    if names is None:names=E.Element(M+'definedNames');book.insert(list(book).index(book.find(M+'sheets'))+1,names)
    for node in list(names):
        if node.get('name')=='_xlnm.Print_Area':names.remove(node)
    for i,sheet in enumerate(book.find(M+'sheets')):
        area=f'$A$1:$T${last}'if i==0 else'$A$1:$D$'+str(max(int(r.get('r'))for r in E.fromstring(parts[layout['history']]).find(M+'sheetData')))
        E.SubElement(names,M+'definedName',name='_xlnm.Print_Area',localSheetId=str(i)).text="'"+sheet.get('name').replace("'","''")+"'!"+area
    parts['xl/workbook.xml']=E.tostring(book,encoding='utf-8',xml_declaration=True)
