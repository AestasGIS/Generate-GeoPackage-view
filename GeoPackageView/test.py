"""
Model exported as python.
Name : flood_raster_polygon2
Group : 
With QGIS : 34202
"""

from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterBand
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterProviderConnection
from qgis.core import QgsProcessingParameterDatabaseSchema
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsExpression
from qgis import processing


class Flood_raster_polygon2(QgsProcessingAlgorithm):

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        self.addParameter(QgsProcessingParameterRasterLayer('flood_raster_layer_or_file', 'Flood raster layer or file', defaultValue=None))
        self.addParameter(QgsProcessingParameterBand('layer_number_for_flood_raster_layer', 'Layer number for flood raster layer', parentLayerParameterName='flood_raster_layer_or_file', allowMultiple=False, defaultValue=[1]))
        self.addParameter(QgsProcessingParameterBoolean('is_depth_values_in_centimeters_', 'Is depth values in centimeters ? ', defaultValue=True))
        self.addParameter(QgsProcessingParameterProviderConnection('database_connection', 'Database connection', 'postgres', defaultValue=None))
        self.addParameter(QgsProcessingParameterDatabaseSchema('schema_flood_data', 'Schema, flood data', connectionParameterName='database_connection', defaultValue='fdc_flood'))
        self.addParameter(QgsProcessingParameterEnum('return_period_of_flood', 'Return period of flood', options=['T1','T5','T10','T20','T50','T100','T200','T500','T1000'], allowMultiple=False, usesStaticStrings=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('year', 'Year', type=QgsProcessingParameterNumber.Integer, minValue=2000, maxValue=3000, defaultValue=2025))
        self.addParameter(QgsProcessingParameterEnum('climate_scenario', 'Climate scenario', options=['(none)','SSP1-2.6','SSP2-4.5','SSP3-7.0'], allowMultiple=False, usesStaticStrings=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterString('append_text_to_tablename', 'Append text to tablename', optional=True, multiLine=False, defaultValue=None))

    def processAlgorithm(self, parameters: dict[str, Any], context: QgsProcessingContext, model_feedback: QgsProcessingFeedback) -> dict[str, Any]:
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(6, model_feedback)
        results = {}
        outputs = {}

        # Calculate expression
        alg_params = {
            'INPUT': QgsExpression("replace(trim(lower(concat(\r\n  array_get(array('T1','T5','T10','T20','T50','T100','T200','T500','T1000'),@return_period_of_flood),\r\n  '_',\r\n  @year,\r\n  array_get(array('','_SSP1-2.6','_SSP2-4.5','_SSP3-7.0'),@climate_scenario),\r\n  if (coalesce(@append_text_to_tablename,'')='','','_'||@append_text_to_tablename)))),\r\narray(' ','.','-','æ','ø','å'),array('_','_','_','ae','oe','aa'))\r\n ").evaluate()
        }
        outputs['CalculateExpression'] = processing.run('native:calculateexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Raster pixels to polygons
        alg_params = {
            'FIELD_NAME': 'depth',
            'INPUT_RASTER': parameters['flood_raster_layer_or_file'],
            'RASTER_BAND': parameters['layer_number_for_flood_raster_layer'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RasterPixelsToPolygons'] = processing.run('native:pixelstopolygons', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Refactor fields
        alg_params = {
            'FIELDS_MAPPING': [{'alias': None,'comment': None,'expression': 'if (@depth_in_centimeters_, "depth"/100.0, "depth")','length': 7,'name': 'vanddybde_m','precision': 2,'sub_type': 0,'type': 6,'type_name': 'double precision'}],
            'INPUT': outputs['RasterPixelsToPolygons']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RefactorFields'] = processing.run('native:refactorfields', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Calculate expression2
        alg_params = {
            'INPUT': QgsExpression('concat (\r\n\'WITH one AS (SELECT * FROM fdc_admin.parametre WHERE name LIKE \\\'t_flood_%\\\' AND POSITION(\\\'\', \r\n@schema_flood_data, \r\n\'\\\' in value) > 0 AND POSITION(\\\'\', \r\n@Calculate_expression_OUTPUT, \r\n\'\\\' in value) > 0 \',\r\n\'UNION (SELECT * FROM fdc_admin.parametre WHERE name LIKE \\\'t_flood_%\\\' AND COALESCE(value,\\\'\\\') = \\\'\\\'\',\' ORDER BY name ASC LIMIT 1) ORDER BY value DESC LIMIT 1), \',\r\n\'two   AS (UPDATE fdc_admin.parametre SET value = \\\'"\', \r\n@schema_flood_data,\r\n\'"."\', \r\n@Calculate_expression_OUTPUT,\r\n\'"\\\' WHERE name in (SELECT name FROM one)), \',\r\n\'three AS (UPDATE fdc_admin.parametre SET value = \\\'"fid"\\\' WHERE name in (SELECT \\\'f_pkey_\\\'||name FROM one)), \',\r\n\'four AS (UPDATE fdc_admin.parametre SET value = \\\'"vanddybde_m"\\\' WHERE name in (SELECT \\\'f_depth_\\\'||name FROM one)) \',\r\n\'UPDATE fdc_admin.parametre SET value = \\\'"geom"\\\' WHERE name in (SELECT \\\'f_geom_\\\'||name FROM one);\'\r\n)\r\n').evaluate()
        }
        outputs['CalculateExpression2'] = processing.run('native:calculateexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Export to PostgreSQL (available connections)
        alg_params = {
            'ADDFIELDS': False,
            'APPEND': False,
            'A_SRS': None,
            'CLIP': False,
            'DATABASE': parameters['database_connection'],
            'DIM': 0,  # 2
            'GEOCOLUMN': 'geom',
            'GT': None,
            'GTYPE': 5,  # POLYGON
            'INDEX': False,
            'INPUT': outputs['RefactorFields']['OUTPUT'],
            'LAUNDER': False,
            'MAKEVALID': False,
            'OPTIONS': None,
            'OVERWRITE': True,
            'PK': 'fid',
            'PRECISION': True,
            'PRIMARY_KEY': None,
            'PROMOTETOMULTI': False,
            'SCHEMA': parameters['schema_flood_data'],
            'SEGMENTIZE': None,
            'SHAPE_ENCODING': None,
            'SIMPLIFY': None,
            'SKIPFAILURES': False,
            'SPAT': None,
            'S_SRS': None,
            'TABLE': outputs['CalculateExpression']['OUTPUT'],
            'T_SRS': None,
            'WHERE': None
        }
        outputs['ExportToPostgresqlAvailableConnections'] = processing.run('gdal:importvectorintopostgisdatabaseavailableconnections', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # PostgreSQL execute SQL
        alg_params = {
            'DATABASE': parameters['database_connection'],
            'SQL': outputs['CalculateExpression2']['OUTPUT']
        }
        outputs['PostgresqlExecuteSql'] = processing.run('native:postgisexecutesql', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        return results

    def name(self) -> str:
        return 'flood_raster_polygon2'

    def displayName(self) -> str:
        return 'flood_raster_polygon2'

    def group(self) -> str:
        return ''

    def groupId(self) -> str:
        return ''

    def createInstance(self):
        return self.__class__()
