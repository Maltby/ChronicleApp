const AWS = require('aws-sdk')
const {Client} = require('pg')

// import passwords
// var env = process.env.NODE_ENV || 'development';
// var secrets = require('./secrets')[env];
var secrets = require('./secrets');

AWS.config.update({region: 'us-east-1'})
var rds = new AWS.RDS()

// Connect to RDS, wait until DB is active
exports.handler = function(event, context, callback) {

    if (event.searchTerm === undefined) {
        return callback(null, "400 No search term specified")
    }

    var searchTerm = event.searchTerm

    rds.waitFor('dBSnapshotAvailable', function(err, data) {
        if (err) {
            console.log(err, err.stack)
            callback(err, null)
        }
        else {
            // Query most recent 100 articles
            query(searchTerm, function(final) {
                console.log(final)
                callback(null, final)
            })
        }
    })
}

function query(searchTerm, _callback) {
    rds.describeDBInstances({DBInstanceIdentifier:'booksmain'}, function(err, data) {
        if (err) {
            console.log('ERROR: ')
            console.log(err, err.stack)
            return _callback(err)
        }
        // Obtain neccessary information to create client, then connect
        var endpoint = data.DBInstances[0].Endpoint.Address
        const client = new Client({
            user: secrets.user,
            host: endpoint,
            database: secrets.db,
            password: secrets.password,
            port: secrets.port
        })
        client.connect()
        console.log('connected to client')

        // Search term query of titles and authors
        client.query(`SELECT id, title, author, listens, s3audioLocation FROM booksmain WHERE to_tsvector(title || ' ' || author) @@ to_tsquery('(${searchTerm})') AND available = true`, (err, res) => {
            console.log('attemted query')
            if (err){
                console.log(err)
                client.end()
                return _callback(err)
            } 
            client.end()
            _callback(res['rows'])
        })
    })
}