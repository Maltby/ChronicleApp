//
//  SearchViewController.swift
//  MySampleApp
//
//  Created by Brice Maltby on 11/23/17.
//

import UIKit
import AWSAuthUI
import AWSAuthCore

class SearchViewController: UIViewController, UITableViewDelegate, UITableViewDataSource, UISearchBarDelegate {
    
    var booksArray: [Book] = []
    
    fileprivate let loginButton: UIBarButtonItem = UIBarButtonItem(title: nil, style: .done, target: nil, action: nil)
    
    func onSignIn (_ success: Bool) {
        // handle successful sign in
        if (success) {
            self.setupRightBarButtonItem()
        } else {
            // handle cancel operation from user
        }
    }
    @IBOutlet weak var searchBar: UISearchBar!
    
    @IBOutlet weak var activityView: UIView!
    @IBOutlet weak var activityIndicator: UIActivityIndicatorView!
    
    @IBOutlet weak var mainTableView: UITableView!
    @IBOutlet weak var mainTableViewBottomConstraint: NSLayoutConstraint!
    @IBOutlet weak var currentBookView: UIView!
    @IBOutlet weak var currentBookViewHeight: NSLayoutConstraint!
    @IBOutlet weak var currentBookTitle: UILabel!
    
    @IBOutlet weak var currentPlayPauseButton: UIButton!
    @IBAction func currentPlayPauseButtonAction(_ sender: Any) {
        if AVPlayerSharedInstance.sharedInstance.isPlaying == true {
            AVPlayerSharedInstance.sharedInstance.player.pause()
            AVPlayerSharedInstance.sharedInstance.isPlaying = false
            currentPlayPauseButton.titleLabel?.text = "Play"
            currentPlayPauseButton.setTitle("Play", for: .normal)
        } else {
            AVPlayerSharedInstance.sharedInstance.player.play()
            AVPlayerSharedInstance.sharedInstance.isPlaying = true
            currentPlayPauseButton.setTitle("Pause", for: .normal)
        }
    }
    
    var mainViewTap: UITapGestureRecognizer?
    
    override func viewWillAppear(_ animated: Bool) {
        setupView()
        if self.navigationController != nil {
            let navigationController = self.navigationController!
            navigationController.navigationBar.barTintColor = UIColor.init(red: 255/255, green: 211/255, blue: 0, alpha: 1.0)
        }
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        activityView.backgroundColor = UIColor.white
        activityIndicator.hidesWhenStopped = true
        
        activityView.isHidden = false
        
        searchBar.delegate = self
        searchBar.placeholder = "Search for book or author"
        
        mainTableView.delegate = self
        mainTableView.dataSource = self
        mainTableView.rowHeight = UITableViewAutomaticDimension
        mainTableView.estimatedRowHeight = 100
        
        if self.navigationController as? UINavigationController != nil {
            let navigationController = self.navigationController as! UINavigationController
            navigationController.navigationBar.barTintColor = UIColor.init(red: 255/255, green: 211/255, blue: 0, alpha: 1.0)
        }
        
        self.setupRightBarButtonItem()
        navigationItem.backBarButtonItem = UIBarButtonItem(title: "Back", style: .plain, target: nil, action: nil)
        
        // Default theme settings.
        navigationController!.navigationBar.backgroundColor = UIColor(red: 1.0, green: 1.0, blue: 1.0, alpha: 1.0)
        navigationController!.navigationBar.barTintColor = UIColor(red: 0xF5/255.0, green: 0x85/255.0, blue: 0x35/255.0, alpha: 1.0)
        navigationController!.navigationBar.tintColor = UIColor.white
        presentSignInViewController()
        
        mainViewTap = UITapGestureRecognizer(target: self, action: #selector(SearchViewController.dismissKeyboard))
    }
    
    func querySearchString(queryString: String){
        activityView.isHidden = false
        activityView.backgroundColor = UIColor.white
        activityIndicator.startAnimating()
        awsSearchBooks(queryString: queryString) {
            (result: [Book]) in
            self.booksArray = result
            DispatchQueue.main.async {
                self.activityView.isHidden = true
                self.activityIndicator.stopAnimating()
                self.mainTableView.reloadData()
            }
        }
    }
    
    func awsSearchBooks(queryString: String, completion: @escaping (_ result: [Book]) -> Void) {
        let client = AWSSearchTermQueryAPIClient.default()
        var arrayOfBooks: [Book] = []
        client.rootGet(searchTerm: queryString).continueWith { (task: AWSTask) -> AWSBooksQueryResponse? in
            if let error = task.error {
                print("Error occurred: \(error)")
                return nil
            }
            if let result = task.result {
                let mutableResults = result.mutableCopy() as! NSArray
                if mutableResults != [] {
                    var tempArray: [Book] = []
                    for book in mutableResults {
                        let bookResponse = book as! AWSBooksQueryResponse
                        let bookObject = Book.init(id: bookResponse.id, title: bookResponse.title, author: bookResponse.author, listens: bookResponse.listens, s3bookcoverlocation: bookResponse.s3bookcoverlocation, s3audiolocation: bookResponse.s3audiolocation)
                        tempArray.append(bookObject)
                    }
                    arrayOfBooks = tempArray
                    completion(arrayOfBooks)
                }
            }
            return nil
        }
    }
    
    
    func searchBarTextDidBeginEditing(_ searchBar: UISearchBar) {
        if (mainViewTap != nil) {
            view.addGestureRecognizer(mainViewTap!)
        }
    }
    
    func searchBarTextDidEndEditing(_ searchBar: UISearchBar) {
        let query = searchBar.text
        dismissKeyboard()
        if query != "" {querySearchString(queryString: query!)}
    }
    
    func searchBarCancelButtonClicked(_ searchBar: UISearchBar) {
        searchBar.text = ""
    }
    
    func searchBarSearchButtonClicked(_ searchBar: UISearchBar) {
        let query = searchBar.text
        dismissKeyboard()
        if query != "" {querySearchString(queryString: query!)}
    }
    
    func setupView() {
        // No book playing, hide currentBook player
        if AVPlayerSharedInstance.sharedInstance.book?.id == nil {
            currentBookView.isHidden = true
            currentPlayPauseButton.isHidden = true
            currentBookTitle.isHidden = true
            mainTableViewBottomConstraint.constant = -(currentBookViewHeight.constant)
        } else {
            // Book currently playing
            currentBookView.isHidden = false
            currentPlayPauseButton.isHidden = false
            currentBookTitle.isHidden = false
            
            currentBookViewHeight.constant = 66
            mainTableViewBottomConstraint.constant = 0
            
            let currentViewTap = UITapGestureRecognizer(target: self, action:  #selector (self.segueToDetail (_:)))
            currentBookView.addGestureRecognizer(currentViewTap)
            
            currentBookTitle.text = AVPlayerSharedInstance.sharedInstance.book?.title
            if AVPlayerSharedInstance.sharedInstance.isPlaying == true {
                currentPlayPauseButton.setTitle("Pause", for: .normal)
            } else {
                currentPlayPauseButton.setTitle("Play", for: .normal)
            }
            
        }
    }
    
    @objc func segueToDetail(_ sender:(UITapGestureRecognizer)) {
        let book = AVPlayerSharedInstance.sharedInstance.book
        let detailVC = storyboard?.instantiateViewController(withIdentifier: "DetailViewController") as! DetailViewController
        detailVC.book = book
        navigationController?.pushViewController(detailVC, animated: true)
    }
    
//    func pushBooksToTableView(books: Array<Any>) {
//        booksArray = []
//        for book in books {
//            let bookResponse = book as! AWSBooksQueryResponse
//            booksArray.append(bookResponse)
//        }
//        DispatchQueue.main.async {
//            self.activityView.isHidden = true
//            self.activityIndicator.stopAnimating()
//            self.mainTableView.reloadData()
//        }
//    }
    
    func setupRightBarButtonItem() {
        navigationItem.rightBarButtonItem = loginButton
        navigationItem.rightBarButtonItem!.target = self
        
        if (AWSSignInManager.sharedInstance().isLoggedIn) {
            navigationItem.rightBarButtonItem!.title = NSLocalizedString("Sign-Out", comment: "Label for the logout button.")
            //            navigationItem.rightBarButtonItem!.action = #selector(MainViewController.handleLogout)
        }
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
    
    func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        var cell:UITableViewCell? =
            mainTableView.dequeueReusableCell(withIdentifier: "BookListCell") as? UITableViewCell
        if (cell == nil)
        {
            cell = UITableViewCell(style: UITableViewCellStyle.subtitle, reuseIdentifier: "BookListCell")
        }
        let bookItem = booksArray[indexPath.row]
        
        cell!.textLabel?.numberOfLines = 0
        cell!.textLabel?.lineBreakMode = .byWordWrapping
        
        cell!.detailTextLabel?.numberOfLines = 0
        cell!.detailTextLabel?.lineBreakMode = .byWordWrapping
        
        cell!.textLabel?.text = bookItem.title
        cell!.detailTextLabel?.text = bookItem.author
        
        cell!.setNeedsLayout()
        
        return cell!
    }
    
    func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return booksArray.count
    }
    
    func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        mainTableView.deselectRow(at: indexPath, animated: true)
        print("Selected \(indexPath.row)")
        let book = booksArray[indexPath.row]
        let detailVC = storyboard?.instantiateViewController(withIdentifier: "DetailViewController") as! DetailViewController
        detailVC.book = book
        navigationController?.pushViewController(detailVC, animated: true)
    }
    
    @objc func dismissKeyboard() {
        //Causes the view (or one of its embedded text fields) to resign the first responder status.
        if (mainViewTap != nil) {
            view.removeGestureRecognizer(mainViewTap!)
        }
        view.endEditing(true)
    }
    
    func handleLogout() {
        if (AWSSignInManager.sharedInstance().isLoggedIn) {
            AWSSignInManager.sharedInstance().logout(completionHandler: {(result: Any?, error: Error?) in
                self.navigationController!.popToRootViewController(animated: false)
                self.setupRightBarButtonItem()
                self.presentSignInViewController()
            })
        } else {
            assert(false)
        }
    }
}
