from ddgs import DDGS

def search_for_articles(search_txt):
    with DDGS() as ddgs:
        results = list(ddgs.text(
            search_txt,
            region="wt-wt",
            safesearch="off",
            max_results=3
        ))
        
        return results
    
if __name__ == "__main__":
    results= search_for_articles("Agile debelopment")
    for res in results:
        print(res['href'])