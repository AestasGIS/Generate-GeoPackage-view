import re

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QCheckBox, QVBoxLayout, QComboBox
from qgis.core import QgsProject, QgsLayerTreeModel, QgsVectorLayer, QgsWkbTypes, QgsProviderRegistry
from qgis.gui import QgsLayerTreeView

class ChooseLayer(QDialog):
    def __init__(self,names):
        super().__init__()

        self.setWindowTitle("Vælg lag, som skal konverteres til permanent view")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.cbbx = QComboBox()
        self.cbbx.addItems(names)
        self.cbbx.setCurrentIndex(0)        

        self.rs = QCheckBox()
        self.rs.setText ('Replace original datasource ?')


        layout = QVBoxLayout()
        layout.addWidget(self.cbbx)
        layout.addWidget(self.rs)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

# Main

layers = [l for l in QgsProject().instance().mapLayers().values() 
    if  isinstance(l, QgsVectorLayer) 
    and l.dataProvider().storageType()=='GPKG'
    and l.dataProvider().subsetString().lower().find('select') >= 0]

if len(layers) > 0: 
    dlg = ChooseLayer([n.name() for n in layers])
    if dlg.exec():
        layer = layers[dlg.cbbx.currentIndex()]
        layerProvider = layer.dataProvider()
        layerStorage = layerProvider.storageType()
        file_path = layerProvider.dataSourceUri().split('|')[0]
        subset = layerProvider.subsetString()
        pkid = layer.fields()[layer.primaryKeyAttributes()[0]].name()
        table_name = layer.name().lower().replace('æ','ae').replace('ø','oe').replace('å','aa')
        table_name = re.sub('[^a-zA-Z0-9_\n\.]', '_', table_name)
        table_name = re.sub('_{2,}','_', table_name)
        
        sqltxt = 'CREATE VIEW {} AS {}'.format(table_name,subset)
        
        if layer.isSpatial():
            data_type = 'features'
            identifier = table_name 
            ext = layer.extent()
            min_x = ext.xMinimum()
            max_x = ext.xMaximum()
            min_y = ext.yMinimum()
            max_y = ext.yMaximum()
            srs_id = layer.crs().authid().replace('EPSG:','')
            
            column_name = layerProvider.geometryColumnName()
            z= 0
            m = 0
            geometry_type_name = QgsWkbTypes.displayString(layer.wkbType()).upper() 
            if geometry_type_name[-1] == 'M':
                m = 1
                geometry_type_name = geometry_type_name[:-1]
            if geometry_type_name[-1] == 'Z':
                z = 1
                geometry_type_name = geometry_type_name[:-1]
                    
        else: 
        
            data_type = 'attributes'
            identifier = table_name 
            min_x = NULL
            max_x = NULL
            min_y = NULL
            max_y = NULL
            srs_id = 0
        
        sql1txt = 'INSERT INTO gpkg_contents (table_name,data_type,identifier,min_x,min_y,max_x,max_y,srs_id) VALUES (\'{}\',\'{}\',\'{}\',{},{},{},{},{});'.format(table_name,data_type,identifier,min_x,min_y,max_x,max_y,srs_id)
        
        if data_type =='features':
            sql2txt = 'INSERT INTO gpkg_geometry_columns(table_name,column_name,geometry_type_name,srs_id,z,m) VALUES (\'{}\',\'{}\',\'{}\',{},{},{})'.format(table_name,column_name,geometry_type_name,srs_id,z,m);
        else:
            sql2txt = ''
        
        md = QgsProviderRegistry.instance().providerMetadata("ogr")
        con = md.createConnection( file_path, {})
        con.executeSql (sqltxt)
        con.executeSql (sql1txt)
        if sql2txt != '': con.executeSql (sql2txt)
        
        if dlg.rs.isChecked():
            layerProvider.setSubsetString('')
            layer.setDataSource(file_path + '|layername='+table_name, layer.name(),'ogr')
            layer.reload()

