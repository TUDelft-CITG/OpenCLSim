## Start server

``` bash
# Set Flask app
set FLASK_APP=server.py

# Set Flask environment
set FLASK_ENV=development

# Run Flask
flask run
```

## Run app
Once the the Flask server is running and serving, you can start the Vue application. 

``` bash
# Go to correct folder
cd ../digital-twin-static

# Run app
npm run serve
```