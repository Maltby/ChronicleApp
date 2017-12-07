//
//  DetailViewController.swift
//  MySampleApp
//
//  Created by Brice Maltby on 11/11/17.
//

import UIKit
import AWSAuthCore
import AWSAuthUI
import AWSS3
import AWSUserPoolsSignIn
import AVFoundation

class DetailViewController: UIViewController, UITableViewDataSource, UITableViewDelegate {
    
    var book: Book?
    
    let secrets = Secrets()
    
    var isPlaying: Bool = false {
        didSet {
            if isPlaying == false {
                AVPlayerSharedInstance.sharedInstance.isPlaying = false
                playPauseButton.setTitle("Play", for: .normal)
                stopTimer()
            } else {
                AVPlayerSharedInstance.sharedInstance.isPlaying = true
                playPauseButton.setTitle("Puase", for: .normal)
                startTimer()
            }
        }
    }
    
    var secondsTimer = Timer()
    var maximumTime = Float64()
    var currentTime = CMTime() {
        didSet{
            let currentSeconds : Float64 = CMTimeGetSeconds(currentTime)
            playheadSlider.setValue(Float(currentSeconds), animated: true)
            // TODO : Automatically begin playing next chapter once first chapter ends
//            if currentSeconds == maximumTime {
//                chapterTableView.selectRow(at: NSIndexPath(row: currentChapter!, section: 0) as IndexPath, animated: true, scrollPosition: .middle)
//                chapterTableView.delegate?.tableView!(chapterTableView, didSelectRowAt: (NSIndexPath(row: currentChapter!, section: 0) as IndexPath))
//            }
        }
    }
    @IBAction func favoriteButton(_ sender: Any) {
        addToFavorites()
    }
    
    @IBOutlet weak var playPauseButton: UIButton!
    @IBOutlet weak var playheadSlider: UISlider!
    @IBOutlet weak var fullDurationLabel: UILabel!
    @IBOutlet weak var currentDurationLabel: UILabel!
    
    @IBOutlet weak var bookCoverImageView: UIImageView!
    @IBOutlet weak var chapterTableView: UITableView!
    
    @IBAction func handlePlayPauseButtonPressed(_ sender: UIButton) {
        if AVPlayerSharedInstance.sharedInstance.book != book {
            AVPlayerSharedInstance.sharedInstance.book = book
            chapterTableView.selectRow(at: NSIndexPath(row: 0, section: 0) as IndexPath, animated: true, scrollPosition: .middle)
            chapterTableView.delegate?.tableView!(chapterTableView, didSelectRowAt: (NSIndexPath(row: 0, section: 0) as IndexPath))
            isPlaying = true
        }
        
        else if isPlaying == true {
            AVPlayerSharedInstance.sharedInstance.player.pause()
            isPlaying = false
        }
        else {
            AVPlayerSharedInstance.sharedInstance.player.play()
            isPlaying = true
        }
    }
    @IBAction func handlePlayheadSliderTouchBegin(_ sender: UISlider) {
        AVPlayerSharedInstance.sharedInstance.player.pause()
        stopTimer()
    }
    @IBAction func handlePlayheadSliderValueChanged(_ sender: UISlider) {
        let seconds : Float64 = Float64(playheadSlider.value)
        currentDurationLabel.text = self.stringFromTimeInterval(interval: Double(seconds))
    }
    @IBAction func handlePlayheadSliderTouchEnd(_ sender: UISlider) {
        let seconds : Float64 = Float64(playheadSlider.value)
        let targetTime = CMTimeMakeWithSeconds(seconds, 1)
        
        currentDurationLabel.text = self.stringFromTimeInterval(interval: Double(seconds))
        AVPlayerSharedInstance.sharedInstance.player.seek(to: targetTime)
        AVPlayerSharedInstance.sharedInstance.player.play()
        startTimer()
    }
    
    func onSignIn (_ success: Bool) {
        // handle successful sign in
        if (success) {
//            self.setupRightBarButtonItem()
        } else {
            // handle cancel operation from user
        }
    }
    
    var chapters = [NSDictionary]()
    
    var currentChapter: Int? {
        didSet {
            AVPlayerSharedInstance.sharedInstance.currentChapter = currentChapter
        }
    }
    
    override func viewWillAppear(_ animated: Bool) {
        if self.navigationController != nil {
            let navigationController = self.navigationController! 
            navigationController.navigationBar.barTintColor = UIColor.init(red: 255/255, green: 211/255, blue: 0, alpha: 1.0)
        }
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        chapters = [(book?.s3audiolocation)!]
        
        chapterTableView.delegate = self
        chapterTableView.dataSource = self
        chapterTableView.reloadData()
        
        if self.navigationController != nil {
            let navigationController = self.navigationController!
            navigationController.navigationBar.barTintColor = UIColor.init(red: 255/255, green: 211/255, blue: 0, alpha: 1.0)
            navigationItem.rightBarButtonItem = UIBarButtonItem(title: "Add", style: .plain, target: self, action: #selector(addToFavorites))
        }
        
        presentSignInViewController()
        
        getPreSignedURLCredentials()
        
        if AVPlayerSharedInstance.sharedInstance.book?.id == nil {
            AVPlayerSharedInstance.sharedInstance.book = book
            chapterTableView.selectRow(at: NSIndexPath(row: 0, section: 0) as IndexPath, animated: true, scrollPosition: .middle)
            chapterTableView.delegate?.tableView!(chapterTableView, didSelectRowAt: (NSIndexPath(row: 0, section: 0) as IndexPath))
        }
        else if AVPlayerSharedInstance.sharedInstance.book != book {
            print("waiting for user to select row")
        } else {
            continueBook()
        }
        loadBookCover()
    }
    
    func getPreSignedURLCredentials() {
        let credentialProvider = AWSCognitoCredentialsProvider(regionType: .USEast1, identityPoolId: secrets.preSignedURL["identityPoolId"]!)
        let configuration = AWSServiceConfiguration(region: .USEast2, credentialsProvider: credentialProvider)
        AWSS3PreSignedURLBuilder.register(with: configuration!, forKey: secrets.preSignedURL["forKey"]!)
    }
    
    @objc func addToFavorites() {
        let client = AWSAddToFavoritesClient.default()
        var favoriteBookString = ""
        if let bookId = book?.id {
            favoriteBookString = "\(bookId)"
            client.rootGet(bookId: favoriteBookString).continueWith{ (task: AWSTask) -> Empty? in
                if let error = task.error {
                    print("Error occurred: \(error)")
                    return nil
                }
                
                if let result = task.result {
                    print("Book has been added")
                }
                return nil
            }
        }
    }
    
    func pullAudioFromS3(chapter: Int) {
        if let url = (book?.s3audiolocation![String(chapter)] as! NSDictionary)["s3Location"] as? String {
            let builder = AWSS3PreSignedURLBuilder.s3PreSignedURLBuilder(forKey: "USEast2S3PreSignedURLBuilder")
            let request = AWSS3GetPreSignedURLRequest.init()
            request.bucket = "books-to-mp3"
            request.key = url
            request.httpMethod = AWSHTTPMethod.GET
            
            let oneDayFromNow = NSDate(timeIntervalSinceNow:86400)
            request.expires = oneDayFromNow as Date
            
            builder.getPreSignedURL(request).continueWith { (task: AWSTask) -> Any? in
                if task.error != nil {
                    print("Error occured requesting pre-signed url: \(String(describing: task.error))")
                } else if let url = task.result {
                    // TODO: put in a completion handler, often returns zero, create catch
                    let duration = AVPlayerSharedInstance.sharedInstance.streamBook(url: url)
                    DispatchQueue.main.async {
                        self.beginBook(duration: duration)
                    }
                    
                }
                return nil
            }
        }
    }
    
    func loadBookCover() {
        if let url = (book?.s3bookcoverlocation) {
            let builder = AWSS3PreSignedURLBuilder.s3PreSignedURLBuilder(forKey: "USEast2S3PreSignedURLBuilder")
            let request = AWSS3GetPreSignedURLRequest.init()
            request.bucket = "book-cover-image"
            request.key = url
            request.httpMethod = AWSHTTPMethod.GET
            
            let oneDayFromNow = NSDate(timeIntervalSinceNow:86400)
            request.expires = oneDayFromNow as Date
            
            builder.getPreSignedURL(request).continueWith { (task: AWSTask) -> Any? in
                if task.error != nil {
                    print("Error occured requesting pre-signed url: \(String(describing: task.error))")
                } else if let url = task.result {
                    // TODO: put in a completion handler, often returns zero, create catch
                    self.downloadImage(url: url as URL)
                }
                return nil
            }
        }
        
    }
    
    func getDataFromUrl(url: URL, completion: @escaping (Data?, URLResponse?, Error?) -> ()) {
        URLSession.shared.dataTask(with: url) { data, response, error in
            completion(data, response, error)
            }.resume()
    }
    
    func downloadImage(url: URL) {
        print("Download Started")
        getDataFromUrl(url: url) { data, response, error in
            guard let data = data, error == nil else { return }
            print(response?.suggestedFilename ?? url.lastPathComponent)
            print("Download Finished")
            DispatchQueue.main.async() {
                self.bookCoverImageView.image = UIImage(data: data)
            }
        }
    }
    
    func beginBook(duration: CMTime) {
        maximumTime = CMTimeGetSeconds(duration)
        fullDurationLabel.text = self.stringFromTimeInterval(interval: maximumTime)
        playheadSlider.minimumValue = 0
        playheadSlider.maximumValue = Float(maximumTime)
        playheadSlider.isContinuous = true
        
        currentTime = AVPlayerSharedInstance.sharedInstance.player.currentTime()
        let currentSeconds : Float64 = CMTimeGetSeconds(currentTime)
        currentDurationLabel.text = self.stringFromTimeInterval(interval: currentSeconds)
        
        setUpButtons()
        AVPlayerSharedInstance.sharedInstance.player.volume = 1.0
        AVPlayerSharedInstance.sharedInstance.player.play()
        isPlaying = true
    }
    
    func continueBook() {
        if AVPlayerSharedInstance.sharedInstance.player.currentItem?.asset.duration != nil {
            let fullDuration : CMTime = (AVPlayerSharedInstance.sharedInstance.player.currentItem?.asset.duration)!
            let fullSeconds : Float64 = CMTimeGetSeconds(fullDuration)
            fullDurationLabel.text = self.stringFromTimeInterval(interval: fullSeconds)
            playheadSlider.minimumValue = 0
            playheadSlider.maximumValue = Float(fullSeconds)
            playheadSlider.isContinuous = true
            
            currentTime = AVPlayerSharedInstance.sharedInstance.player.currentTime()
            let currentSeconds : Float64 = CMTimeGetSeconds(currentTime)
            currentDurationLabel.text = self.stringFromTimeInterval(interval: currentSeconds)
            
            setUpButtons()
            AVPlayerSharedInstance.sharedInstance.player.volume = 1.0
            AVPlayerSharedInstance.sharedInstance.player.play()
            isPlaying = true
            
            AVPlayerSharedInstance.sharedInstance.book = book
            if AVPlayerSharedInstance.sharedInstance.currentChapter != nil {
                chapterTableView.selectRow(at: NSIndexPath(row: (AVPlayerSharedInstance.sharedInstance.currentChapter! - 1), section: 0) as IndexPath, animated: true, scrollPosition: .middle)
            }
        } else {
            AVPlayerSharedInstance.sharedInstance.book = book
            if AVPlayerSharedInstance.sharedInstance.currentChapter != nil {
                chapterTableView.selectRow(at: NSIndexPath(row: (AVPlayerSharedInstance.sharedInstance.currentChapter! - 1), section: 0) as IndexPath, animated: true, scrollPosition: .middle)
            }
            
        }
    }
    
    func startTimer() {
        secondsTimer = Timer.scheduledTimer(timeInterval: 1, target: self, selector: #selector(self.updateSlider), userInfo: nil, repeats: true)
    }
    
    func stopTimer() {
        secondsTimer.invalidate()
    }
    
    @objc func updateSlider(timer: Timer) {
//        currentTime = player.currentTime()
        currentTime = AVPlayerSharedInstance.sharedInstance.player.currentTime()
        let currentSeconds : Float64 = CMTimeGetSeconds(currentTime)
        currentDurationLabel.text = self.stringFromTimeInterval(interval: currentSeconds)
        playheadSlider.setValue(Float(currentSeconds), animated: true)
        
        if Float(currentSeconds) >= playheadSlider.maximumValue {
            timer.invalidate()
        }
    }
    
    func setUpButtons() {
        playheadSlider.addTarget(self, action: #selector(self.handlePlayheadSliderTouchBegin), for: .touchDown)
        playheadSlider.addTarget(self, action:    #selector(self.handlePlayheadSliderTouchEnd), for: .touchUpInside)
        playheadSlider.addTarget(self, action: #selector(self.handlePlayheadSliderTouchEnd), for: .touchUpOutside)
        playheadSlider.addTarget(self, action: #selector(self.handlePlayheadSliderValueChanged), for: .valueChanged)
    }
    
    func stringFromTimeInterval(interval: TimeInterval) -> String {
        let interval = Int(interval)
        let seconds = interval % 60
        let minutes = (interval / 60) % 60
        let hours = (interval / 3600)
        return String(format: "%02d:%02d:%02d", hours, minutes, seconds)
    }
    
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return (book?.s3audiolocation?.allKeys.count)!
    }
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = chapterTableView.dequeueReusableCell(withIdentifier: "chapterCell", for: indexPath)
        let stringIndex = String(indexPath.row + 1)
        let chapter = book?.s3audiolocation?[stringIndex] as! NSDictionary
        cell.textLabel?.text = chapter["Title"] as! String
        return cell
    }

    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        if book == AVPlayerSharedInstance.sharedInstance.book {
            if AVPlayerSharedInstance.sharedInstance.currentChapter == indexPath.row + 1 {
                print("same chapter selected")
            } else {
                currentChapter = indexPath.row + 1
                DispatchQueue.global().async {
                    self.pullAudioFromS3(chapter: indexPath.row + 1)
                }
            }
        } else {
            DispatchQueue.global().async {
                self.pullAudioFromS3(chapter: indexPath.row + 1)
            }
        }
        AVPlayerSharedInstance.sharedInstance.book = book
        
        let cell = chapterTableView.dequeueReusableCell(withIdentifier: "chapterCell", for: indexPath)
    }
    
    override func didReceiveMemoryWarning() {
        super.didReceiveMemoryWarning()
        // Dispose of any resources that can be recreated.
    }
    
    func presentSignInViewController() {
        if !AWSSignInManager.sharedInstance().isLoggedIn {
            let config = AWSAuthUIConfiguration()
            config.enableUserPoolsUI = true
            config.canCancel = false
            
            AWSAuthUIViewController.presentViewController(with: self.navigationController!,
                                                          configuration: config,
                                                          completionHandler: { (provider: AWSSignInProvider, error: Error?) in
                                                            if error != nil {
                                                                print("Error occurred: \(String(describing: error))")
                                                            } else {
                                                                self.onSignIn(true)
                                                            }
            })
        }
    }
    
    func handleLogout() {
        if (AWSSignInManager.sharedInstance().isLoggedIn) {
            AWSSignInManager.sharedInstance().logout(completionHandler: {(result: Any?, error: Error?) in
                self.navigationController!.popToRootViewController(animated: false)
//                self.setupRightBarButtonItem()
                self.presentSignInViewController()
            })
//            print("Logout Successful: \(signInProvider.getDisplayName)");
        } else {
            assert(false)
        }
    }
    
    

}
