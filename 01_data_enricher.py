import pandas as pd
from rdflib import Graph, Literal, Namespace, BNode
from rdflib.namespace import RDF, RDFS, XSD, FOAF, OWL
import spacy
import re
import logging


class OlympicsKnowledgeEnricher:
    def __init__(self):
        self.g = Graph()
        self.jo = Namespace("http://example.org/jo-2024/") 
        self.setup_namespaces()
        self.setup_nlp()
        self.setup_logging()
        self.medalists = set()
        self.date_pattern = r"(\d{1,2}(?:er)?\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})"
        self.score_pattern = r"(\d+)(?:\s*-\s*\d+)?\s*points?"
        self.medal_pattern = r"médaille\s+(d'or|d'argent|de bronze)"
        
        self.logger.info("Chargement des données du graphe existant...")
        self.g.parse("og24_data.ttl", format="turtle")
        self.logger.info(f"Graphe chargé avec {len(self.g)} triplets")

    def setup_namespaces(self):
        self.g.bind("jo", self.jo)
        self.g.bind("rdf", RDF)
        self.g.bind("rdfs", RDFS)
        self.g.bind("foaf", FOAF)
        self.g.bind("xsd", XSD)
        self.g.bind("owl", OWL)

    def setup_nlp(self):
        try:
            self.nlp = spacy.load("fr_core_news_lg")
        except:
            logging.warning("Modèle fr_core_news_lg non trouvé, installation...")
            import os
            os.system("python -m spacy download fr_core_news_lg")
            self.nlp = spacy.load("fr_core_news_lg")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _create_event_uri(self, row):
        event_id = re.sub(r'[^a-zA-Z0-9]', '', row['Event'])
        return self.jo[f"event_{event_id}"]

    def _create_athlete_uri(self, row):
        athlete_id = re.sub(r'[^a-zA-Z0-9]', '', row['Name'])
        return self.jo[f"athlete_{athlete_id}"]

    def _create_result_uri(self, row):
        event_id = re.sub(r'[^a-zA-Z0-9]', '', row['Event'])
        athlete_id = re.sub(r'[^a-zA-Z0-9]', '', row['Name'])
        return self.jo[f"result_{athlete_id}_{event_id}"]

    def _create_article_uri(self, row):
        article_id = re.sub(r'[^a-zA-Z0-9]', '', row['title'])[:50]
        date_str = row['date'].replace('-', '')
        return self.jo[f"article_{date_str}_{article_id}"]

    def _get_athlete_uri(self, athlete_name):
        athlete_id = re.sub(r'[^a-zA-Z0-9]', '', athlete_name)
        return self.jo[f"athlete_{athlete_id}"]

    def _add_event_triples(self, event_uri, row):
        self.g.add((event_uri, RDF.type, self.jo.SportingEvent))
        self.g.add((event_uri, RDFS.label, Literal(row['Event'])))
        self.g.add((event_uri, self.jo.discipline, Literal(row['Discipline'])))
        self.g.add((event_uri, self.jo.disciplineCode, Literal(row['Code_Discipline'])))
        self.g.add((event_uri, self.jo.date, Literal(row['Medal_date'], datatype=XSD.date)))

    def _add_athlete_triples(self, athlete_uri, row):
        self.g.add((athlete_uri, RDF.type, self.jo.Athlete))
        self.g.add((athlete_uri, RDFS.label, Literal(row['Name'])))
        self.g.add((athlete_uri, FOAF.gender, Literal(row['Gender'])))
        self.g.add((athlete_uri, self.jo.representCountry, Literal(row['Country'])))
        self.g.add((athlete_uri, self.jo.countryCode, Literal(row['Country_code'])))
        self.g.add((athlete_uri, self.jo.isQualified, Literal(True, datatype=XSD.boolean)))
        
        if 'Personal_Best' in row and pd.notna(row['Personal_Best']):
            self.g.add((athlete_uri, self.jo.personalBest, Literal(row['Personal_Best'], datatype=XSD.decimal)))
            
        if 'Discipline' in row and pd.notna(row['Discipline']):
            discipline_uri = self.jo[f"discipline_{re.sub(r'[^a-zA-Z0-9]', '', row['Discipline'])}"]
            self.g.add((athlete_uri, self.jo.participatesIn, discipline_uri))
            self.g.add((discipline_uri, RDF.type, self.jo.Discipline))
            self.g.add((discipline_uri, RDFS.label, Literal(row['Discipline'])))

    def _add_result_triples(self, result_uri, row, event_uri, athlete_uri):
        self.g.add((result_uri, RDF.type, self.jo.Result))
        self.g.add((result_uri, self.jo.medalType, Literal(row['Medal_type'])))
        self.g.add((result_uri, self.jo.medalCode, Literal(row['Medal_code'], datatype=XSD.integer)))
        self.g.add((result_uri, self.jo.date, Literal(row['Medal_date'], datatype=XSD.date)))
        
        self.g.add((result_uri, self.jo.achievedBy, athlete_uri))
        self.g.add((result_uri, self.jo.inEvent, event_uri))
        self.g.add((event_uri, self.jo.hasResult, result_uri))

    def _add_article_metadata(self, article_uri, row):
        self.g.add((article_uri, RDF.type, self.jo.Article))
        self.g.add((article_uri, RDFS.label, Literal(row['title'])))
        self.g.add((article_uri, self.jo.source, Literal(row['source'])))
        self.g.add((article_uri, self.jo.date, Literal(row['date'], datatype=XSD.date)))
        self.g.add((article_uri, self.jo.content, Literal(row['content'])))

    def convert_time_to_decimal(self, time_str):
        if ':' not in time_str:
            return time_str
        h, m, s = map(int, time_str.split(':'))
        return f"{h*60 + m + s/60:.2f}"

    def process_medals_data(self, medals_csv):
        self.logger.info("Traitement des données de médailles...")
        df = pd.read_csv(medals_csv, delimiter=';')
        
        for _, row in df.iterrows():
            event_uri = self._create_event_uri(row)
            athlete_uri = self._create_athlete_uri(row)
            result_uri = self._create_result_uri(row)
            
            if 'Performance' in row and pd.notna(row['Performance']):
                row['Performance'] = self.convert_time_to_decimal(str(row['Performance']))
            if 'Personal_Best' in row and pd.notna(row['Personal_Best']):
                row['Personal_Best'] = self.convert_time_to_decimal(str(row['Personal_Best']))

            self._add_event_triples(event_uri, row)
            self._add_athlete_triples(athlete_uri, row)
            self._add_result_triples(result_uri, row, event_uri, athlete_uri)
            
            if row['Medal_type'] == 'Gold Medal':
                self.medalists.add(row['Name'])

    def extract_event_details(self, article_uri, text):
        doc = self.nlp(text)
        
        event_patterns = {
            'performance': r"([0-9]{1,2}[,.][0-9]{2})\s*secondes?",
            'time': r"([0-9]{1,2}[:][0-9]{2})[,.][0-9]{2}",
            'attendance': r"([0-9]{1,6})\s*(?:spectateurs|places)",
            'phase': r"(finale|demi-finale|séries)\s+du\s+([^\"\.]+)",
            'record': r"(?:nouveau\s+)?record\s+(olympique|du monde|personnel|historique|français)",
            'medals': r"([0-9]+)\s*médailles?\s*(d'or|d'argent|de bronze)?",
            'points': r"([0-9]+)\s*points",
            'cost': r"([0-9]+)\s*millions?\s*d'euros",
            'tickets': r"([0-9,.]+)\s*millions?\s*de\s*billets",
            'audience': r"([0-9,.]+)\s*millions?\s*de\s*spectateurs\s*(?:à la télévision)?"
        }
        
        for pattern_name, pattern in event_patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                detail = BNode()
                self.g.add((detail, RDF.type, self.jo.EventDetail))
                self.g.add((detail, self.jo.extractedFrom, article_uri))
                self.g.add((detail, RDFS.label, Literal(match.group(0))))
                self.g.add((detail, self.jo.detailType, Literal(pattern_name)))
                
                # Valeur numérique si disponible
                if match.groups():
                    self.g.add((detail, self.jo.value, Literal(match.group(1))))

    def extract_athlete_details(self, article_uri, text):
        doc = self.nlp(text)
        
        for medalist in self.medalists:
            if medalist in text:
                context = self._get_context(text, medalist)
                athlete_uri = self._get_athlete_uri(medalist)
                
                age_match = re.search(r"âgé[e]? de ([0-9]{1,2}) ans", context)
                if age_match:
                    self.g.add((athlete_uri, self.jo.age, 
                              Literal(int(age_match.group(1)), datatype=XSD.integer)))

                perf_match = re.search(r"([0-9]{1,2}[,.][0-9]{2})\s*secondes", context)
                if perf_match:
                    perf = perf_match.group(1).replace(',', '.')
                    self.g.add((athlete_uri, self.jo.performance, 
                              Literal(float(perf), datatype=XSD.decimal)))
                    
                discipline_match = re.search(r"discipline\s*:\s*([a-zA-Z\s]+)", context, re.IGNORECASE)
                if discipline_match:
                    discipline_name = discipline_match.group(1).strip()
                    discipline_uri = self.jo[f"discipline_{re.sub(r'[^a-zA-Z0-9]', '', discipline_name)}"]
                    self.g.add((athlete_uri, self.jo.participatesIn, discipline_uri))
                    self.g.add((discipline_uri, RDF.type, self.jo.Discipline))
                    self.g.add((discipline_uri, RDFS.label, Literal(discipline_name)))

    def _get_context(self, text, term, window=100):
        start = max(0, text.find(term) - window)
        end = min(len(text), text.find(term) + len(term) + window)
        return text[start:end]

    def enrich_from_articles(self, articles_csv):
        self.logger.info("Enrichissement à partir des articles...")
        df = pd.read_csv(articles_csv)
        
        for _, row in df.iterrows():
            article_uri = self._create_article_uri(row)
            self._add_article_metadata(article_uri, row)
            
            self.extract_event_details(article_uri, row['content'])
            self.extract_athlete_details(article_uri, row['content'])
            self._extract_venue_details(article_uri, row['content'])

    def _extract_venue_details(self, article_uri, text):
        venues = {
            'Stade de France': {
                'capacity': 80000,
                'location': 'Saint-Denis'
            },
            'Arena Paris La Défense': {
                'capacity': 15000,
                'location': 'Nanterre'
            },
            'Centre Aquatique Olympique': {
                'capacity': 5000,
                'location': 'Saint-Denis'
            },
            'Arena Porte de la Chapelle': {
                'capacity': 8000,
                'location': 'Paris'
            },
            'Accor Arena': {
                'capacity': 15000,
                'location': 'Paris'
            },
            'Paris Aquatics Centre': {
                'capacity': 5000,
                'location': 'Saint-Denis'
            },
        }
        
        for venue_name, details in venues.items():
            if venue_name in text:
                venue_uri = self.jo[re.sub(r'[^a-zA-Z]', '', venue_name)]
                self.g.add((venue_uri, RDF.type, self.jo.Venue))
                self.g.add((venue_uri, RDFS.label, Literal(venue_name)))
                self.g.add((venue_uri, self.jo.capacity, 
                          Literal(details['capacity'], datatype=XSD.integer)))
                self.g.add((venue_uri, self.jo.location, Literal(details['location'])))
                
                attendance_match = re.search(rf"{venue_name}.*?([0-9]+)\s*spectateurs", text)
                if attendance_match:
                    self.g.add((venue_uri, self.jo.attendance, 
                              Literal(int(attendance_match.group(1)), datatype=XSD.integer)))

    def save_graph(self, output_file):
        self.logger.info(f"Sauvegarde du graphe dans {output_file}")
        self.g.serialize(destination=output_file, format="turtle")
        self.logger.info(f"Graphe sauvegardé avec {len(self.g)} triplets")


class WeatherEnricher:
    def __init__(self, graph):
        self.g = graph
        self.jo = Namespace("http://example.org/jo-2024/")
        self.schema1 = Namespace("http://schema.org/")
        self.oplwthr = Namespace("http://www.openlinksw.com/schemas/weatherreport#")
        
        self.g.bind("jo", self.jo)
        self.g.bind("schema1", self.schema1)
        self.g.bind("oplwthr", self.oplwthr)

    def _create_weather_uri(self, venue_uri):
        venue_id = str(venue_uri).split('/')[-1]
        return self.jo[f"weather_{venue_id}"]

    def _format_temperature(self, temp_str):
        try:
            temp_kelvin = float(temp_str)  # Car l'API renvoie une température en Kelvin
            temp_celsius = temp_kelvin - 273.15
            return f"{temp_celsius:.1f}"
        except ValueError:
            return temp_str

    def enrich_events_with_weather(self):
        logging.info("Enrichissement des événements avec la météo...")
        
        venue_query = """
            PREFIX jo: <http://example.org/jo-2024/>
            PREFIX schema1: <http://schema.org/>
            
            SELECT DISTINCT ?venue ?lat ?long
            WHERE {
                ?venue schema1:geo ?geo .
                ?geo a schema1:GeoCoordinates ;
                    schema1:latitude ?lat ;
                    schema1:longitude ?long .
            }
        """
        
        venues = self.g.query(venue_query)
        for v in venues:
            print(v, '\n')
        
        for venue_result in venues:
            venue = venue_result.venue
            lat = int(float(venue_result.lat))  # Obligé car le docker du prof ne traite pas correctement les floats
            long = int(float(venue_result.long))  # Obligé car le docker du prof ne traite pas correctement les floats
            
            service_url = f"http://localhost/service/weather/getWeather?latitude={lat}&longitude={long}"
            
            weather_report_uri = self._create_weather_uri(venue)
            
            weather_query = f"""
                CONSTRUCT {{
                    ?event jo:hasWeatherReport <{str(weather_report_uri)}> .
                    <{str(weather_report_uri)}> a jo:WeatherReport ;
                            jo:temperature ?temp ;
                            jo:description ?desc ;
                            jo:venue <{str(venue)}> .
                }}
                WHERE {{
                    ?event jo:hasVenue <{str(venue)}> .
                    SERVICE <{service_url}> {{
                        [] oplwthr:temperature ?temp ;
                           schema1:description ?desc .
                    }}
                }}
            """
            
            try:
                self.g.remove((None, self.jo.hasWeatherReport, weather_report_uri))
                self.g.remove((weather_report_uri, None, None))
                
                weather_data = self.g.query(weather_query)
                formatted_weather = []
                for triple in weather_data:
                    if triple[1] == self.jo.temperature:
                        temp = self._format_temperature(triple[2])
                        formatted_weather.append((triple[0], triple[1], Literal(temp, datatype=XSD.decimal)))
                    else:
                        formatted_weather.append(triple)
                
                self.g += formatted_weather
                logging.info(f"Météo ajoutée pour {venue}")
            except Exception as e:
                logging.error(f"Erreur lors de la récupération de la météo pour {venue}: {e}")
                continue


def main():
    enricher = OlympicsKnowledgeEnricher()
    weather_enricher = WeatherEnricher(enricher.g)
    
    enricher.process_medals_data('csv/olympic_medals_2024.csv')
    
    enricher.enrich_from_articles('csv/articles_jo2024.csv')
    
    venue_count = len(list(enricher.g.subjects(RDF.type, enricher.jo.Venue)))
    logging.info(f"Nombre de venues trouvées : {venue_count}")
    weather_enricher.enrich_events_with_weather()
    
    enricher.save_graph('og24_data_enriched.ttl')

if __name__ == "__main__":
    main()