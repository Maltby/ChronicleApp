//
//  UserSharedInstance.swift
//  MySampleApp
//
//  Created by Brice Maltby on 11/19/17.
//

import UIKit
import AWSAuthCore
import AWSUserPoolsSignIn

class UserSharedInstance: NSObject {
    static let sharedInstance = UserSharedInstance()
    var identityId = String()
    
    let secrets = Secrets()
    
    func getIdentityId() -> String {
        if identityId != nil {
            return identityId
        } else {
            let serviceConfiguration = AWSServiceConfiguration(region: .USEast1, credentialsProvider: nil)
            let userPoolConfiguration = AWSCognitoIdentityUserPoolConfiguration(clientId: secrets.userPoolSecrets["clientId"]!, clientSecret: secrets.userPoolSecrets["clientSecret"]!, poolId: secrets.userPoolSecrets["poolId"]!)
            AWSCognitoIdentityUserPool.register(with: serviceConfiguration, userPoolConfiguration: userPoolConfiguration, forKey: "UserPool")
            let pool = AWSCognitoIdentityUserPool(forKey: "UserPool")
            let credentialsProvider = AWSCognitoCredentialsProvider(regionType: .USEast1, identityPoolId: secrets.userPoolSecrets["identityPoolId"]!, identityProviderManager:pool)
            self.identityId = credentialsProvider.identityId!
            
            AWSServiceManager.default().defaultServiceConfiguration = AWSServiceConfiguration.init(region: .USEast1, credentialsProvider: credentialsProvider)
        }
        return identityId
    }
}
