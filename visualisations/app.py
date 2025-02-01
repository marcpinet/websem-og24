from flask import Flask, render_template, request, jsonify
from rdflib import Graph, Namespace
from SPARQLWrapper import SPARQLWrapper, JSON
import json

app = Flask(__name__)

g = Graph()
g.parse("og24_data_enriched_and_linked.ttl", format="turtle")

jo = Namespace("http://example.org/jo-2024/")
dbr = Namespace("http://dbpedia.org/resource/")
dbo = Namespace("http://dbpedia.org/ontology/")

# REQUETES SPARQL COMPLEXES POUR LA VISUALISATION DES DONNEES
QUERIES = {
    "medailles_par_pays": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?country (COUNT(DISTINCT ?gold) as ?goldCount) 
               (COUNT(DISTINCT ?silver) as ?silverCount)
               (COUNT(DISTINCT ?bronze) as ?bronzeCount)
        WHERE {
            ?athlete jo:representCountry ?countryUri .
            BIND(REPLACE(str(?countryUri), "http://dbpedia.org/resource/", "") as ?country)
            OPTIONAL {
                ?gold jo:achievedBy ?athlete ;
                      jo:medalType "Gold Medal" .
            }
            OPTIONAL {
                ?silver jo:achievedBy ?athlete ;
                        jo:medalType "Silver Medal" .
            }
            OPTIONAL {
                ?bronze jo:achievedBy ?athlete ;
                        jo:medalType "Bronze Medal" .
            }
        }
        GROUP BY ?country
        HAVING (COUNT(DISTINCT ?gold) > 0 || COUNT(DISTINCT ?silver) > 0 || COUNT(DISTINCT ?bronze) > 0)
        ORDER BY DESC(?goldCount) DESC(?silverCount) DESC(?bronzeCount)
    """,
    
    "get_countries": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX dbr: <http://dbpedia.org/resource/>
        
        SELECT DISTINCT ?country
        WHERE {
            ?athlete jo:representCountry ?countryUri .
            BIND(REPLACE(str(?countryUri), "http://dbpedia.org/resource/", "") as ?country)
        }
        ORDER BY ?country
    """,
    
    "events_by_venue": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?venueName (COUNT(DISTINCT ?event) as ?eventCount)
        WHERE {
            ?event jo:hasVenue ?venue .
            ?venue rdfs:label ?venueName .
            FILTER NOT EXISTS { ?venueName rdf:type ?any }
        }
        GROUP BY ?venueName
        ORDER BY DESC(?eventCount)
    """,
    
    "events_by_sport": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?sportName (COUNT(DISTINCT ?athlete) as ?eventCount)
        WHERE {
            ?athlete a jo:Athlete ;
                    jo:participatesIn ?sport .
            ?sport rdfs:label ?sportName .
        }
        GROUP BY ?sportName
        ORDER BY DESC(?eventCount)
    """,
    
    "events_timeline": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        SELECT ?date (COUNT(DISTINCT ?event) as ?eventCount)
        WHERE {
            ?event jo:date ?date .
        }
        GROUP BY ?date
        ORDER BY ?date
    """,
    
    "weather_by_venue": """
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?venueName ?description ?temperature
        WHERE {
        ?weather a jo:WeatherReport ;
                jo:description ?description ;
                jo:temperature ?temperature ;
                jo:venue ?venue .
        ?venue rdfs:label ?venueName .
        }
        ORDER BY ?venueName
    """,
}

def process_sparql_results(qres):
    results = []
    for row in qres:
        result = {}
        for key in row.labels:
            value = row[key]
            if value is None:
                result[str(key)] = ""
            else:
                if isinstance(value, (int, float)):
                    result[str(key)] = str(value)
                else:
                    result[str(key)] = str(value).replace('_', ' ')
        results.append(result)
    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute_query', methods=['POST'])
def execute_query():
    query_name = request.json.get('query_name')
    if query_name in QUERIES:
        try:
            qres = g.query(QUERIES[query_name])
            results = process_sparql_results(qres)
            return jsonify({'success': True, 'results': results})
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Query not found'})

@app.route('/athletes_by_country', methods=['POST'])
def athletes_by_country():
    country = request.json.get('country')
    if not country:
        return jsonify({'success': False, 'error': 'Country not specified'})
    
    athletes_query = f"""
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbr: <http://dbpedia.org/resource/>

        SELECT DISTINCT ?name ?sportLabel ?medalType
        WHERE {{
            ?athlete a jo:Athlete ;
                    rdfs:label ?name ;
                    jo:representCountry ?countryUri .
            FILTER(CONTAINS(LCASE(STR(?countryUri)), LCASE("{country}")))
            OPTIONAL {{
                ?athlete jo:participatesIn ?sport .
                ?sport rdfs:label ?sportLabel .
            }}
            OPTIONAL {{
                ?result jo:achievedBy ?athlete ;
                        jo:medalType ?medalType .
            }}
        }}
        ORDER BY ?name
    """
    
    try:
        qres = g.query(athletes_query)
        results = process_sparql_results(qres)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"Error fetching athletes for country: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/athlete_details/<athlete_name>')
def athlete_details(athlete_name):
    athlete_query = f"""
        PREFIX jo: <http://example.org/jo-2024/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        
        SELECT ?propertyLabel ?value
        WHERE {{
            ?athlete rdfs:label "{athlete_name}"@en .
            ?athlete ?property ?value .
            BIND(STRAFTER(STR(?property), "http://example.org/jo-2024/") as ?propertyLabel)
            FILTER(?property != rdfs:label)
        }}
    """
    
    try:
        qres = g.query(athlete_query)
        results = process_sparql_results(qres)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"Error fetching athlete details: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)