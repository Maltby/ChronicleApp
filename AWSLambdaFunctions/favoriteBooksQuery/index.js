const AWS = require('aws-sdk')
const {Client} = require('pg')

AWS.config.update({region: 'us-east-1'})
var rds = new AWS.RDS()

var secrets = require('./secrets')

exports.handler = function(event, context, callback) {
    console.log("received request")

    //Ensure user id was passed to handler
    if (event.id === undefined) {
        return callback("400 caller has no identity");
    }

    var id = event.id
    console.log('cognitoIdentityId: ', id)
    // Connect to RDS, wait until DB is active
    rds.waitFor('dBSnapshotAvailable', function(err, data) {
        if (err) {
            console.log(err, err.stack)
            return callback(err, null)
        }
        query(id, function(err, finalList) {
            if (err) {
                console.log(err)
                return callback(err, null)
            } 
            console.log('finalList: ')
            console.log(finalList)
            callback(null, finalList)
        })
    })
}

function query(id, queryCallback) {
    //Connect to users RDS database, 
    queryFavorites(id, function(err, favoritesList) {
        if (err) {
            console.log(err)
            return queryCallback(err, null)
        } 
        console.log(`favoritesList: ${favoritesList}`)
        queryItems(favoritesList, function(err, bookList) {
            if (err) {
                console.log(err)
                queryCallback(err, null)
            } else {
                console.log(bookList)
                queryCallback(null, bookList)
            }
        })
    })
}

function queryFavorites(id, favListCallback) {
    rds.describeDBInstances({DBInstanceIdentifier:'chronicleusers'}, function(err, data) {
        if (err) {
            console.log('ERROR: ')
            console.log(err, err.stack)
            return favListCallback(err, null)
        }
        var endpoint = data.DBInstances[0].Endpoint.Address
        // Pull keys from "secrets"
        const usersDb = new Client({
            user: secrets.chronicleusers.user,
            host: endpoint,
            database: secrets.chronicleusers.db,
            password: secrets.chronicleusers.password,
            port: secrets.chronicleusers.port
        })
        usersDb.connect()
        console.log('connected to client')

        // Query list of users favorite books
        usersDb.query(`SELECT favorites FROM usersmain WHERE id = '${id}'`, (err, res) => {
            console.log('attemted query')
            if (err){
                console.log('received error')
                console.log(err)
                usersDb.end()
                return favListCallback(err, null)
            } 
            console.log('received response')
            var json = Array(res.rows[0]["favorites"])
            console.log(`result: ${json}`)
            usersDb.end()
            // Return list of favorite book ids to queryItems
            favListCallback(null, json)
        })
    })
}

function queryItems(bookIdArray, bookListCallback) {
    console.log('queryItems called')
    rds.describeDBInstances({DBInstanceIdentifier:'booksmain'}, function(err, data) {
        if (err) {
            console.log('ERROR: ')
            console.log(err, err.stack)
            return bookListCallback(err, null)
        }
        var endpoint = data.DBInstances[0].Endpoint.Address
        const booksDb = new Client({
            user: secrets.booksmain.user,
            host: endpoint,
            database: secrets.booksmain.db,
            password: secrets.booksmain.password,
            port: secrets.booksmain.port
        })
        booksDb.connect()
        console.log('connected to booksDb')

        //Query list of favorite books
        booksDb.query(`SELECT id, title, author, listens, s3audioLocation FROM booksmain WHERE id IN (${bookIdArray}) ORDER BY title DESC`, (err, res) => {
            console.log('attemted query')
            if (err){
                console.log(err)
                booksDb.end()
                return bookListCallback(err, null)
            } 
            booksDb.end()
            if (res['rows'] === []) {
                return itemsCallback("400 Book ID's undefined", null)
            } 
            console.log(`res['rows]`)
            console.log(res['rows'])
            bookListCallback(null, res['rows'])
        })
    })
}