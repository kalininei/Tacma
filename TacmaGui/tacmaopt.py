import xml.etree.ElementTree as ET
import os.path
import bproc


class ProgOptions(object):
    # These options could be changed before cls.read() procedure
    opt_fn = 'tacmaOpt.xml'
    wdir = '.'
    ver = '0'

    def __init__(self):
        """ call read() before using ProgOptions object """
        #default values
        self.wfile = 'tacmaData.xml'
        #main window size and position
        self.Hx, self.Hy = 800, 300
        self.x0, self.y0 = 0, 0
        #autosave in minutes
        self.autosave = 2
        #backup
        self.backup_fn = 'tacmaData.xml.backup'
        self.backup_autosave = 20
        #update window each %s seconds
        self.update_interval = 2
        #archivate actual data when it exceed %s weeks
        self.archivate = 20
        #minimum number of weeks in actual file
        self.minactual = 5

    def title(self):
        return 'Tacma v.' + self.ver

    def _towd(self, f):
        '->str. Build absolute file path'
        return os.path.join(self.wdir, f)

    def _fnames_to_wd(self):
        self.opt_fn = self._towd(os.path.basename(self.opt_fn))
        self.wfile = self._towd(os.path.basename(self.wfile))
        self.backup_fn = self._towd(os.path.basename(self.backup_fn))

    def new_archive_filename(self):
        index = 1
        stem = "archiveData"
        while 1:
            fn = stem + str(index) + ".xml"
            fn = self._towd(fn)
            if not os.path.isfile(fn):
                return fn
            else:
                index += 1

    def write(self):
        'writes options to default file'
        root = ET.Element('TacmaOptions')
        root.attrib['version'] = self.ver

        ET.SubElement(root, 'ADATAFILE').text = os.path.basename(self.wfile)
        ET.SubElement(root, 'ASAVE_INTERVAL').text = str(self.autosave)
        ET.SubElement(root, 'BDATAFILE').text = \
            os.path.basename(self.backup_fn)
        ET.SubElement(root, 'BSAVE_INTERVAL').text = str(self.backup_autosave)
        w = ET.SubElement(root, 'MAIN_WINDOW')
        ET.SubElement(w, 'HX').text = str(self.Hx)
        ET.SubElement(w, 'HY').text = str(self.Hy)
        ET.SubElement(w, 'X0').text = str(self.x0)
        ET.SubElement(w, 'Y0').text = str(self.y0)
        ET.SubElement(root, 'UPDATE_INT').text = str(self.update_interval)
        ET.SubElement(root, 'ARCHIVATE').text = str(self.archivate)
        ET.SubElement(root, 'MINACTUAL').text = str(self.minactual)

        bproc.xmlindent(root)
        tree = ET.ElementTree(root)
        tree.write(self.opt_fn, xml_declaration=True, encoding='utf-8')

    def read(self):
        'tries to read data from default location'
        self._fnames_to_wd()
        try:
            root = ET.parse(self.opt_fn)
        except Exception as e:
            print 'Error loading options file: %s' % str(e)

        try:
            self.wfile = self._towd(root.find('ADATAFILE').text)
        except:
            pass
        try:
            self.backup_fn = self._towd(root.fine('BDATAFILE').text)
        except:
            pass
        try:
            self.autosave = float(root.find('ASAVE_INTERVAL').text)
        except:
            pass
        try:
            self.backup_autosave = float(root.find('BSAVE_INTERVAL').text)
        except:
            pass
        try:
            self.archivate = int(root.find("ARCHIVATE").text)
        except:
            pass
        try:
            self.minactual = int(root.find("MINACTUAL").text)
        except:
            pass
        try:
            self.Hx = int(root.find('MAIN_WINDOW/HX').text)
            self.Hy = int(root.find('MAIN_WINDOW/HY').text)
            self.x0 = int(root.find('MAIN_WINDOW/X0').text)
            self.y0 = int(root.find('MAIN_WINDOW/Y0').text)
        except:
            pass
        try:
            self.update_interval = int(root.find('UPDATE_INT').text)
        except:
            pass

opt = ProgOptions()
