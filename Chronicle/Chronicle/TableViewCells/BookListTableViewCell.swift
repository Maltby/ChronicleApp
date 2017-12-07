//
//  BookListTableViewCell.swift
//  MySampleApp
//
//  Created by Brice Maltby on 12/3/17.
//

import UIKit

class BookListTableViewCell: UITableViewCell {
    
    override func systemLayoutSizeFitting(_ targetSize: CGSize, withHorizontalFittingPriority horizontalFittingPriority: UILayoutPriority, verticalFittingPriority: UILayoutPriority) -> CGSize {
        
        self.layoutIfNeeded()
        var size = super.systemLayoutSizeFitting(targetSize, withHorizontalFittingPriority: horizontalFittingPriority, verticalFittingPriority: verticalFittingPriority)
        
        if let textLabel = self.textLabel, let detailTextLabel = self.detailTextLabel {
            let detailHeight = detailTextLabel.frame.size.height
            if detailTextLabel.frame.origin.x > textLabel.frame.origin.x { // style = Value1 or Value2
                let textHeight = textLabel.frame.size.height
                if (detailHeight > textHeight) {
                    size.height += detailHeight - textHeight
                }
            } else { // style = Subtitle, so always add subtitle height
                size.height += detailHeight
            }
        }
        
        return size
        
    }
    
}

