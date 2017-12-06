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
    
    var book = AWSBooksQueryResponse()
    var currentChapter : Int?
    var isPlaying: Bool = false
    
    func streamBook(url:NSURL) -> CMTime {
        try! AVAudioSession.sharedInstance().setCategory(AVAudioSessionCategoryPlayback, with: [])
        print("playing \(url)")
//        let playerItem = AVPlayerItem(url: url as URL)
//        player = AVPlayer(playerItem:playerItem)
        do {
            self.player = try AVPlayer(url: url as URL)
        } catch let error as NSError {
            print(error)
        } catch {
            print("AVPlayer init failed")
        }
        
//        player = AVPlayer.init(url: url as URL)
        let duration = player.currentItem?.asset.duration
        return duration!
    }
    
}
