//
//  AVPlayerSharedInstance.swift
//  MySampleApp
//
//  Created by Brice Maltby on 11/14/17.
//

import UIKit
import AVFoundation

class AVPlayerSharedInstance: NSObject {
    static let sharedInstance = AVPlayerSharedInstance()
    var player = AVPlayer()
    
    var book: Book?
    var currentChapter : Int?
    var isPlaying: Bool = false
    
    func streamBook(url:NSURL) -> CMTime {
        try! AVAudioSession.sharedInstance().setCategory(AVAudioSessionCategoryPlayback, with: [])
        print("playing \(url)")
        do {
            self.player = try AVPlayer(url: url as URL)
        } catch let error as NSError {
            print(error)
        } catch {
            print("AVPlayer init failed")
        }
        
        let duration = player.currentItem?.asset.duration
        return duration!
    }
    
}
