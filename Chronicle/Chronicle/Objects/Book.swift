//
//  Book.swift
//  Chronicle
//
//  Created by Brice Maltby on 12/7/17.
//  Copyright © 2017 Brice Maltby. All rights reserved.
//

import UIKit

class Book: NSObject {
    let id: NSNumber?
    let title: String?
    let author: String?
    let listens: NSNumber?
    let s3bookcoverlocation: String?
    let s3audiolocation: NSDictionary?
    init(id: NSNumber?, title: String?, author: String?, listens: NSNumber?, s3bookcoverlocation: String?, s3audiolocation: NSDictionary?) {
        self.id = id
        self.title = title
        self.author = author
        self.listens = listens
        self.s3bookcoverlocation = s3bookcoverlocation
        self.s3audiolocation = s3audiolocation
        return
    }
}
