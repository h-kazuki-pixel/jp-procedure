"""RDF の設定。基点の URI はここだけで変える。"""
BASE = 'https://w3id.org/jp-procedure/'       # w3id に登録する基点
DEF = BASE + 'def#'                           # 独自の語彙(SurveyRecord など)
PREFIXES = {
    'cpsv': 'http://purl.org/vocab/cpsv#',
    'cv': 'http://data.europa.eu/m8g/',
    'eli': 'http://data.europa.eu/eli/ontology#',
    'dct': 'http://purl.org/dc/terms/',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'prov': 'http://www.w3.org/ns/prov#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'xsd': 'http://www.w3.org/2001/XMLSchema#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'sh': 'http://www.w3.org/ns/shacl#',
    'jpp': DEF,
}
SOURCE_R7 = {'file': 'data/raw/20260826_procedures_survey_result_outline_02.xlsx', 'sheet': 'R7調査結果',
             'url': 'https://www.digital.go.jp/assets/contents/node/basic_page/field_ref_resources/b931f8c1-8598-45ee-91b1-1e9a45acd301/851f67ec/20260826_procedures_survey_result_outline_02.xlsx',
             'page': 'https://www.digital.go.jp/resources/procedures-survey-results', 'header_rows': 2}
