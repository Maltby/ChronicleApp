const AWS = require('aws-sdk')
const {Client} = require('pg')

AWS.config.update({region: 'us-east-1'})
var rds = new AWS.RDS()

var secrets = require('./secrets')

// Connect to RDS, wait until DB is active
exports.handler = function(event, context, callback) {
    console.log("received request")

    if (event.id === undefined) {
        return callback("400 caller has no identity");
    }
    if (event.bookId === undefined) {
        return callback("400 no bookId defined")
    }

    // bookId passed through as query-string, must be converted to int
    var bookId = parseInt(event.bookId)
    var id = event.id
    
    // Ensure db is available
    rds.waitFor('dBSnapshotAvailable', function(err, data) {
        if (err) {
            console.log(err, err.stack)
            return callback(err, null)
        }
        // Add bookId to users favorites list
        addToFavorites(id, bookId, function(err, success) {
            if (err) {
                console.log(err)
                return callback(err, null)
            } 
            console.log("Book has been added to users' favorites")
            callback(null, success)
        })
    })
}

function addToFavorites(id, bookId, addedCallback) {
    rds.describeDBInstances({DBInstanceIdentifier:'chronicleusers'}, function(err, data) {
        if (err) {
            console.log('ERROR: ')
            console.log(err, err.stack)
            return addedCallback(err, null)
        }
        // Obtain neccessary information to create client, then connect
        var endpoint = data.DBInstances[0].Endpoint.Address
        const usersDb = new Client({
            user: secrets.user,
            host: endpoint,
            database: secrets.db,
            password: secrets.password,
            port: secrets.port
        })
        usersDb.connect()
        console.log('connected to client')

        // TODO: Look up race conditions, replace UPDATE with UPSERT
        // Check for existence of row, then either add to row or create row for user if it doesn't exist already
        usersDb.query(`SELECT exists(SELECT FROM usersmain WHERE id='${id}') AS "exists"`, (err, res) => {
            if (err){
                console.log('received error')
                console.log(err)
                userDb.end()
                return addedCallback(err, null)
            } else if (res.rows[0]['exists'] === true) {
                usersDb.query(`UPDATE usersmain SET favorites = favorites || ${bookId} WHERE id = '${id}' AND not(favorites @> array[${bookId}]::INT[])`, (err, res) => {
                    console.log('attemted query')
                    if (err){
                        console.log('received error')
                        console.log(err)
                        usersDb.end()
                        return addedCallback(err, null)
                    } 
                    console.log('success')
                    usersDb.end()
                    addedCallback(null, '200')
                })
            } else {
                usersDb.query(`INSERT INTO usersmain (id, favorites) VALUES ('${id}', '{${bookId}}');`, (err, res) => {
                    console.log('attemted query')
                    if (err){
                        console.log('received error')
                        console.log(err)
                        usersDb.end()
                        return addedCallback(err, null)
                    } 
                    console.log('success')
                    usersDb.end()
                    addedCallback(null, '200')
                })
            }
        })
    })
}