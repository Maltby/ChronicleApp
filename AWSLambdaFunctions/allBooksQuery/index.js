const AWS = require('aws-sdk')
const {Client} = require('pg')

AWS.config.update({region: 'us-east-1'})
var rds = new AWS.RDS()

var secrets = require('./secrets')

// Connect to RDS, wait until DB is active
exports.handler = function(event, context, callback) {
    rds.waitFor('dBSnapshotAvailable', function(err, data) {
        if (err) {
            console.log(err, err.stack)
            callback(err, null)
        }
        else {
            // Query most recent 100 articles
            query(function(final) {
                console.log(final)
                callback(null, final)
            })
        }
    })
}

function query(_callback) {
    rds.describeDBInstances({DBInstanceIdentifier:'booksmain'}, function(err, data) {
        if (err) {
            console.log('ERROR: ')
            console.log(err, err.stack)
            _callback(err)
        }
        else {
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

            // Query most recent 100 articles from postgres
            client.query('SELECT id, title, author, listens, s3audiolocation, s3bookcoverlocation FROM booksmain WHERE available = TRUE ORDER BY listens DESC', (err, res) => {
                console.log('attemted query')
                if (err){
                    console.log(err)
                    client.end()
                    _callback(err)
                } else if (res){
                    client.end()
                    _callback(res['rows'])
                }
            })
        }
    })
}