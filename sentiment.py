import re, math, collections, itertools, os
import nltk, nltk.classify.util, nltk.metrics
from nltk.classify import NaiveBayesClassifier
from nltk.metrics import BigramAssocMeasures
from nltk.metrics import precision, recall, f_measure 
from nltk.probability import FreqDist, ConditionalFreqDist
from nltk.corpus import stopwords

#fancy way of loading files
POLARITY_DATA_DIR = os.path.join('polarityData', 'nt-polaritydata')
RT_POLARITY_POS_FILE = os.path.join(POLARITY_DATA_DIR, 'rt-polarity-pos.txt')
RT_POLARITY_NEG_FILE = os.path.join(POLARITY_DATA_DIR, 'rt-polarity-neg.txt')
stopWords = set(stopwords.words('english'))


def get_words(sentence):
	WordsMod = []
	Words = re.findall(r"[\w']+|[.,!?;]", sentence.rstrip())
	for w in Words:
		if len(w) > 1:
			if w not in stopWords:
				WordsMod.append(w)
	return WordsMod


#FLOW OF THINGS
#OPEN FILE. READ AS SENTENCES. FILTER SENTENCE - REMOVE STOPWORDS. 
# PASS TO FEATURE_SELECT - 


#this function takes a feature selection mechanism and returns its performance in a variety of metrics
def evaluate_features(feature_select):
	posFeatures = []
	negFeatures = []

	#http://stackoverflow.com/questions/367155/splitting-a-string-into-words-and-punctuation
	#breaks up the sentences into lists of individual words (as selected by the input mechanism) and appends 'pos' or 'neg' after each list
	#could be replaced by word_tokenize
	with open(RT_POLARITY_POS_FILE, 'r') as posSentences:
		for i in posSentences:
			posWordsMod = []
			posWordsMod = get_words(i)
			#print("\n Printing poswordsMod: ")
			#print(posWordsMod)
			#feature_select(posWords) is a dictionary 
			posWordsMod = [feature_select(posWordsMod), 'pos']
			posFeatures.append(posWordsMod)
	with open(RT_POLARITY_NEG_FILE, 'r') as negSentences:
		for i in negSentences:
			negWordsMod = []			
			negWordsMod = get_words(i)
			negWordsMod = [feature_select(negWordsMod), 'neg']
			negFeatures.append(negWordsMod)
		
	# posFeatures looks like [....[{'word': True}, 'pos'] , ...]

	#selects 3/4 of the features to be used for training and 1/4 to be used for testing
	posCutoff = int(math.floor(len(posFeatures)*3/4))
	negCutoff = int(math.floor(len(negFeatures)*3/4))
	trainFeatures = posFeatures[:posCutoff] + negFeatures[:negCutoff]
	testFeatures = posFeatures[posCutoff:] + negFeatures[negCutoff:]

	#trains a Naive Bayes Classifier
	classifier = NaiveBayesClassifier.train(trainFeatures)	

	#user_input = raw_input("Enter text for analysis")
	

	#initiates referenceSets and testSets
	referenceSets = collections.defaultdict(set)
	testSets = collections.defaultdict(set)	

	#puts correctly labeled sentences in referenceSets and the predictively labeled version in testsets
	for i, (features, label) in enumerate(testFeatures):
		referenceSets[label].add(i)
		predicted = classifier.classify(features)
		testSets[predicted].add(i)	

	#prints metrics to show how well the feature selection did
	print 'train on %d instances, test on %d instances' % (len(trainFeatures), len(testFeatures))
	print 'accuracy:', nltk.classify.util.accuracy(classifier, testFeatures)
	print 'pos precision:', precision(referenceSets['pos'], testSets['pos'])
	print 'pos recall:', recall(referenceSets['pos'], testSets['pos'])
	print 'neg precision:', precision(referenceSets['neg'], testSets['neg'])
	print 'neg recall:', recall(referenceSets['neg'], testSets['neg'])
	classifier.show_most_informative_features(10)
	test_data = raw_input("Enter text for analysis:  ")
	test_data = get_words(test_data)
	test_data = feature_select(test_data)	
	print 'feature selection', test_data 
	print 'prediction: ',classifier.classify(test_data)


#scores words based on chi-squared test to show information gain (http://streamhacker.com/2010/06/16/text-classification-sentiment-analysis-eliminate-low-information-features/)
def create_word_scores():
	#creates lists of all positive and negative words
	posWords = []
	negWords = []
	with open(RT_POLARITY_POS_FILE, 'r') as posSentences:
		for i in posSentences:
			posWord = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
			posWords.append(posWord)
	with open(RT_POLARITY_NEG_FILE, 'r') as negSentences:
		for i in negSentences:
			negWord = re.findall(r"[\w']+|[.,!?;]", i.rstrip())
			negWords.append(negWord)
	posWords = list(itertools.chain(*posWords))
	negWords = list(itertools.chain(*negWords))

	#build frequency distibution of all words and then frequency distributions of words within positive and negative labels
	word_fd = FreqDist()
	cond_word_fd = ConditionalFreqDist()
	for word in posWords:
		word_fd[word.lower()] += 1
		cond_word_fd['pos'][word.lower()] += 1
	for word in negWords:
		word_fd[word.lower()] += 1
		cond_word_fd['neg'][word.lower()] += 1

	#finds the number of positive and negative words, as well as the total number of words
	pos_word_count = cond_word_fd['pos'].N()
	neg_word_count = cond_word_fd['neg'].N()
	total_word_count = pos_word_count + neg_word_count

	#builds dictionary of word scores based on chi-squared test
	word_scores = {}
	for word, freq in word_fd.iteritems():
		pos_score = BigramAssocMeasures.chi_sq(cond_word_fd['pos'][word], (freq, pos_word_count), total_word_count)
		neg_score = BigramAssocMeasures.chi_sq(cond_word_fd['neg'][word], (freq, neg_word_count), total_word_count)
		word_scores[word] = pos_score + neg_score

	return word_scores

#finds word scores
word_scores = create_word_scores()

#finds the best 'number' words based on word scores
def find_best_words(word_scores, number):
	best_vals = sorted(word_scores.iteritems(), key=lambda (w, s): s, reverse=True)[:number]
	best_words = set([w for w, s in best_vals])
	return best_words

#creates feature selection mechanism that only uses best words
def best_word_features(words):
	return dict([(word, True) for word in words if word in best_words])

#numbers of features to select
numbers_to_test = [10000, 15000]
#tries the best_word_features mechanism with each of the numbers_to_test of features
for num in numbers_to_test:
	print 'evaluating best %d word features' % (num)
	best_words = find_best_words(word_scores, num)
	evaluate_features(best_word_features)
