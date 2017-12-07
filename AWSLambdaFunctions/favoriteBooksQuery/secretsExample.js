var secrets = {
    //postgresql connections details
    booksmain: {
        client: {
            user: 'booksmain root user here',
            port:   'Int(port number here)',
            password: 'user password here',
            db: 'db name here'
        }
    },
    
    chronicleusers: {
        client: {
            user: 'chronicleusers root user here',
            port:   'Int(port number here)',
            password: 'user password here',
            db: 'db name here'
        }
    }
};
exports.secrets = secrets;