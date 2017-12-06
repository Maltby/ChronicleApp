/*
 Copyright 2010-2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.

 Licensed under the Apache License, Version 2.0 (the "License").
 You may not use this file except in compliance with the License.
 A copy of the License is located at

 http://aws.amazon.com/apache2.0

 or in the "license" file accompanying this file. This file is distributed
 on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 express or implied. See the License for the specific language governing
 permissions and limitations under the License.
 */
 

import Foundation
import AWSCore

 
public class AWSBooksQueryResponse : AWSModel {
    
    @objc dynamic var id: NSNumber?
    @objc dynamic var title: String?
    @objc dynamic var author: String?
    @objc dynamic var listens: NSNumber?
    @objc dynamic var s3bookcoverlocation: String?
    @objc dynamic var s3audiolocation: NSDictionary?
    
   	public override static func jsonKeyPathsByPropertyKey() -> [AnyHashable : Any]!{
		var params:[AnyHashable : Any] = [:]
		params["id"] = "id"
		params["title"] = "title"
		params["author"] = "author"
		params["listens"] = "listens"
		params["s3bookcoverlocation"] = "s3bookcoverlocation"
		params["s3audiolocation"] = "s3audiolocation"
		
        return params
	}
//    class func s3audiolocationJSONTransformer() -> ValueTransformer{
//        return ValueTransformer.awsmtl_JSONDictionaryTransformer(withModelClass: AWSBooksQueryResponse_s3audiolocation.self);
//    }
}
