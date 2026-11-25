# Welcome to Microblog!

This is an example application featured in my [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world). See the tutorial for instructions on how to work with it.

The version of the application featured in this repository corresponds to the 2024 edition of the Flask Mega-Tutorial. You can find the 2018 and 2021 versions of the code [here](https://github.com/miguelgrinberg/microblog-2018). And if for any strange reason you are interested in the original code, dating back to 2012, that is [here](https://github.com/miguelgrinberg/microblog-2012).

---

# Tests de charge (atelier 3 EPSI)

Fork de [microblog](https://github.com/miguelgrinberg/microblog) pour faire des tests de charge avec [Locust](https://locust.io).

## Lancer l'application en local

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
flask run --port 5055
```

## Lancer les tests de charge

```bash
cd test/load
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# avec l'interface web (http://localhost:8089)
locust -f locustfile.py --host http://127.0.0.1:5055

# en ligne de commande
locust -f locustfile.py --headless -u 10 -r 5 -t 30s --host http://127.0.0.1:5055
```
