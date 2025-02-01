import rdflib
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, OWL
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm


event_mapping = {
    # Athletics Events
    "Sprint100mMenFinal": "100_metres",
    "MarathonMenFinal": "Marathon_(sport)",
    "Womens100m": "100_metres",
    "Womens100mHurdles": "100_metres_hurdles",
    "Womens400m": "400_metres",
    "Womens10000m": "10,000_metres",
    "MensDecathlon": "Decathlon",
    "WomensHighJump": "High_jump",
    "WomensJavelinThrow": "Javelin_throw",
    "WomensShotPut": "Shot_put",
    "MensDiscusThrow": "Discus_throw",
    "Relay4x100mMenFinal": "4_×_100_metres_relay",

    # Swimming Events
    "Mens100mFreestyle": "100_metre_freestyle",
    "Mens200mFreestyle": "200_metre_freestyle",
    "Mens800mFreestyle": "800_metre_freestyle",
    "Mens200mBreaststroke": "Breaststroke_(swimming)",
    "Womens1500mFreestyle": "1500_metre_freestyle",

    # Combat Sports
    "Mens80kg": "Boxing_at_the_Olympics",
    "Womens57kg": "Boxing_at_the_Olympics",
    "Womens66kg": "Boxing_at_the_Olympics",
    "Men81kg": "Judo_at_the_Olympics",
    "Women70kg": "Judo_at_the_Olympics",
    "MensFreestyle86kg": "Freestyle_wrestling",
    "MensFreestyle97kg": "Freestyle_wrestling",
    "MensFreestyle125kg": "Freestyle_wrestling",
    "MensGrecoRoman67kg": "Greco-Roman_wrestling",
    "MensGrecoRoman87kg": "Greco-Roman_wrestling",

    # Aquatics and Diving
    "Mens3mSpringboard": "Diving_at_the_Olympics",
    "Mens10km": "Marathon_swimming",
    
    # Team Sports Events
    "BasketballMen": "Basketball_at_the_Olympics",
    "BasketballWomen": "Basketball_at_the_Olympics",

    # Cycling Events
    "MensRoadRace": "Road_cycling_at_the_Olympics",
    "WomensCrosscountry": "Mountain_biking_at_the_Olympics",
    
    # Gymnastics
    "MensHorizontalBar": "Horizontal_bar",
    "MensParallelBars": "Parallel_bars",
    "MensRings": "Rings_(gymnastics)",
    "MensVault": "Vault_(gymnastics)",
    
    # Other Sports
    "MensDinghy": "Sailing_at_the_Olympics",
    "WomensKayakCross": "Canoeing_at_the_Olympics",
    "WomensPark": "Skateboarding_at_the_Olympics",
    "WomensStreet": "Skateboarding_at_the_Olympics",
    "WomensSingles": "Badminton_at_the_Olympics",
    "EventingIndividual": "Equestrian_at_the_Olympics",
    "MensSpeed": "Sport_climbing_at_the_Olympics",
    "MensBoulderLead": "Sport_climbing_at_the_Olympics",

    # Shooting Events
    "10mAirRifleMen": "ISSF_10_meter_air_rifle",
    "10mAirRifleWomen": "ISSF_10_meter_air_rifle",
    "50mRifle3PositionsMen": "ISSF_50_meter_rifle_three_positions",
    "50mRifle3PositionsWomen": "ISSF_50_meter_rifle_three_positions",

    # Weightlifting Events
    "Womens59kg": "Weightlifting_at_the_Olympics",
    "Mens73kg": "Weightlifting_at_the_Olympics",
    "Mens89kg": "Weightlifting_at_the_Olympics",
    "Womens81kg": "Weightlifting_at_the_Olympics",

    # Individual Sports
    "WomensIndividual": "Olympic_sports",
    "WomensSabreIndividual": "Fencing_at_the_Olympics",
    "IndividualAllAround": "Rhythmic_gymnastics_at_the_Olympics"
}

# Mappings des sites olympiques
venue_mapping = {
    "StadeDeFrance": "Stade_de_France",
    "AccorArena": "Accor_Arena",
    "RolandGarros": "Stade_Roland_Garros",
    "ArenaParisLaDfense": "Paris_La_Défense_Arena",
    "ParisAquaticsCentre": "Olympic_Aquatics_Centre",
    "CentreAquatiqueOlympique": "Olympic_Aquatics_Centre"
}

# Mappings des équipes nationales
team_mapping = {
    "FranceBasketballMen": "France_national_basketball_team",
    "USABasketballMen": "United_States_men's_national_basketball_team"
}


class KnowledgeGraphLinker:
    def __init__(self, input_file):
        self.g = Graph()
        self.g.parse(input_file, format="turtle")
        self.jo = Namespace("http://example.org/jo-2024/")
        self.dbr = Namespace("http://dbpedia.org/resource/")
        self.dbo = Namespace("http://dbpedia.org/ontology/")
        self.wdt = Namespace("http://www.wikidata.org/entity/")
        self.schema1 = Namespace("http://schema.org/")
        
        self.dbpedia = SPARQLWrapper("http://dbpedia.org/sparql")
        self.wikidata = SPARQLWrapper("https://query.wikidata.org/sparql")
        
        self.g.bind('dbr', self.dbr)
        self.g.bind('dbo', self.dbo)
        self.g.bind('wdt', self.wdt)
        self.g.bind('schema1', self.schema1)
        self.g.bind('owl', OWL)
        
    def search_dbpedia_athlete(self, name):
        query = f"""
            SELECT DISTINCT ?athlete ?name WHERE {{
                ?athlete a dbo:Athlete ;
                        rdfs:label ?name .
                FILTER(CONTAINS(LCASE(?name), LCASE("{name}")))
                FILTER(LANG(?name) = "en")
            }}
        """
        self.dbpedia.setQuery(query)
        self.dbpedia.setReturnFormat(JSON)
        results = self.dbpedia.query().convert()
        
        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["athlete"]["value"]
        return None

    def search_wikidata_athlete(self, name):
        query = f"""
            SELECT DISTINCT ?athlete ?name WHERE {{
                ?athlete wdt:P106 wd:Q2066131 ; # occupation: athlete
                        rdfs:label ?name .
                FILTER(CONTAINS(LCASE(?name), LCASE("{name}")))
                FILTER(LANG(?name) = "en")
            }}
        """
        self.wikidata.setQuery(query)
        self.wikidata.setReturnFormat(JSON)
        results = self.wikidata.query().convert()
        
        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["athlete"]["value"]
        return None

    def search_dbpedia_venue(self, name):
        query = f"""
            SELECT DISTINCT ?venue WHERE {{
                ?venue a dbo:Stadium ;
                      rdfs:label ?name .
                FILTER(CONTAINS(LCASE(?name), LCASE("{name}")))
                FILTER(LANG(?name) = "en")
            }}
        """
        self.dbpedia.setQuery(query)
        self.dbpedia.setReturnFormat(JSON)
        results = self.dbpedia.query().convert()
        
        if results["results"]["bindings"]:
            return results["results"]["bindings"][0]["venue"]["value"]
        return None

    def link_athletes(self, maxi: int = 5):
        athlete_triples = list(self.g.triples((None, RDF.type, self.jo.Athlete)))
        total = min(len(athlete_triples), maxi)
        for i, a in tqdm(enumerate(athlete_triples), total=total, desc="Linking athletes"):
            s, p, o = a
            if i >= maxi:
                break
            name = None
            for _, _, name_literal in self.g.triples((s, RDFS.label, None)):
                name = str(name_literal)
                break
            
            if name:
                dbpedia_uri = self.search_dbpedia_athlete(name)
                if dbpedia_uri:
                    self.g.add((s, OWL.sameAs, URIRef(dbpedia_uri)))
                
                wikidata_uri = self.search_wikidata_athlete(name)
                if wikidata_uri:
                    self.g.add((s, OWL.sameAs, URIRef(wikidata_uri)))

    def link_venues(self, maxi: int = 5):
        venue_triples = list(self.g.triples((None, RDF.type, self.jo.Venue)))
        total = min(len(venue_triples), maxi)
        for i, a in tqdm(enumerate(venue_triples), total=total, desc="Linking venues"):
            s, p, o = a
            if i >= maxi:
                break
            for _, _, name_literal in self.g.triples((s, RDFS.label, None)):
                name = str(name_literal)
                break
            
            if name:
                dbpedia_uri = self.search_dbpedia_venue(name)
                if dbpedia_uri:
                    self.g.add((s, OWL.sameAs, URIRef(dbpedia_uri)))

    def link_events(self, maxi: int = 5):
        # Lier les événements sportifs
        event_triples = list(self.g.triples((None, RDF.type, self.jo.SportingEvent)))
        total = min(len(event_triples), maxi)
        for i, a in tqdm(enumerate(event_triples), total=total, desc="Linking sporting events"):
            s, p, o = a
            
            if i >= maxi:
                break
            
            event_id = str(s).split('/')[-1]
            if event_id in event_mapping:
                dbpedia_uri = self.dbr[event_mapping[event_id]]
                self.g.add((s, OWL.sameAs, dbpedia_uri))
        
        # Lier les sites
        venue_triples = list(self.g.triples((None, RDF.type, self.jo.Venue)))
        total = min(len(venue_triples), maxi)
        for i, a in tqdm(enumerate(venue_triples), total=total, desc="Linking venues"):
            s, p, o = a
            
            if i >= maxi:
                break
            
            venue_id = str(s).split('/')[-1]
            if venue_id in venue_mapping:
                dbpedia_uri = self.dbr[venue_mapping[venue_id]]
                self.g.add((s, OWL.sameAs, dbpedia_uri))
        
        # Lier les équipes
        team_triples = list(self.g.triples((None, RDF.type, self.jo.NationalTeam)))
        total = min(len(team_triples), maxi)
        for i, a in tqdm(enumerate(team_triples), total=total, desc="Linking teams"):
            s, p, o = a
            
            if i >= maxi:
                break
            
            team_id = str(s).split('/')[-1]
            if team_id in team_mapping:
                dbpedia_uri = self.dbr[team_mapping[team_id]]
                self.g.add((s, OWL.sameAs, dbpedia_uri))

    def enrich_with_external_data(self):
        for s, p, o in self.g.triples((None, OWL.sameAs, None)):
            if "dbpedia.org" in str(o):
                query = f"""
                    CONSTRUCT {{
                        <{str(o)}> ?p ?o .
                    }}
                    WHERE {{
                        <{str(o)}> ?p ?o .
                        FILTER(?p IN (dbo:birthDate, dbo:birthPlace, dbo:nationality))
                    }}
                """
                self.dbpedia.setQuery(query)
                self.dbpedia.setReturnFormat('turtle')
                additional_data = self.dbpedia.query().convert()
                # Ajouter les données supplémentaires au graphe
                self.g.parse(data=additional_data, format='turtle')

    def link_all(self):
        print("Liaison des athlètes...")
        self.link_athletes(maxi=5)  # Pour des raisons évidentes de TEMPS
        
        print("Liaison des lieux...")
        self.link_venues(maxi=5)  # Pour des raisons évidentes de TEMPS
        
        print("Liaison des événements...")
        self.link_events(maxi=5)  # Pour des raisons évidentes de TEMPS
        
        print("Enrichissement avec des données externes...")
        self.enrich_with_external_data()

    def save(self, output_file):
        self.g.serialize(destination=output_file, format="turtle")
        print(f"Graphe enrichi sauvegardé dans {output_file}")

if __name__ == "__main__":
    linker = KnowledgeGraphLinker("og24_data_enriched.ttl")
    linker.link_all()
    print("Sauvegarde du graphe enrichi, total de {} triplets".format(len(linker.g)))
    linker.save("og24_data_enriched_and_linked.ttl")