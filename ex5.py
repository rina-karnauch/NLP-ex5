###################################################
# Exercise 5 - Natural Language Processing 67658  #
###################################################

import numpy as np
from matplotlib import pyplot as plt

# subset of categories that we will use
category_dict = {'comp.graphics': 'computer graphics',
                 'rec.sport.baseball': 'baseball',
                 'sci.electronics': 'science, electronics',
                 'talk.politics.guns': 'politics, guns'
                 }


def get_data(categories=None, portion=1.):
    """
    Get data for given categories and portion
    :param portion: portion of the data to use
    :return:
    """
    # get data
    from sklearn.datasets import fetch_20newsgroups
    data_train = fetch_20newsgroups(categories=categories, subset='train', remove=('headers', 'footers', 'quotes'),
                                    random_state=21)
    data_test = fetch_20newsgroups(categories=categories, subset='test', remove=('headers', 'footers', 'quotes'),
                                   random_state=21)

    # train
    train_len = int(portion * len(data_train.data))
    x_train = np.array(data_train.data[:train_len])
    y_train = data_train.target[:train_len]
    # remove empty entries
    non_empty = x_train != ""
    x_train, y_train = x_train[non_empty].tolist(), y_train[non_empty].tolist()

    # test
    x_test = np.array(data_test.data)
    y_test = data_test.target
    non_empty = np.array(x_test) != ""
    x_test, y_test = x_test[non_empty].tolist(), y_test[non_empty].tolist()
    return x_train, y_train, x_test, y_test


# Q1
def linear_classification(portion=1.):
    """
    Perform linear classification
    :param portion: portion of the data to use
    :return: classification accuracy
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score
    tf = TfidfVectorizer(stop_words='english', max_features=1000)
    x_train, y_train, x_test, y_test = get_data(categories=category_dict.keys(), portion=portion)

    tf_train, tf_test = tf.fit_transform(x_train), tf.transform(x_test)
    clf = LogisticRegression().fit(tf_train, y_train)
    y_pred_test = clf.predict(tf_test)
    acc = accuracy_score(y_test, y_pred_test)
    return acc


# Q2
def transformer_classification(portion=1.):
    """
    Transformer fine-tuning.
    :param portion: portion of the data to use
    :return: classification accuracy
    """
    import torch

    class Dataset(torch.utils.data.Dataset):
        """
        Dataset object
        """

        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
            item['labels'] = torch.tensor(self.labels[idx])
            return item

        def __len__(self):
            return len(self.labels)

    from datasets import load_metric
    metric = load_metric("accuracy")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)

    from transformers import Trainer, TrainingArguments
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained('distilroberta-base', cache_dir=None)
    model = AutoModelForSequenceClassification.from_pretrained('distilroberta-base',
                                                               cache_dir=None,
                                                               num_labels=len(category_dict),
                                                               problem_type="single_label_classification")

    x_train, y_train, x_test, y_test = get_data(categories=category_dict.keys(), portion=portion)

    # Add your code here
    training_args = TrainingArguments(learning_rate=2e-5,
                                      num_train_epochs=5,
                                      per_device_train_batch_size=16,
                                      output_dir="NLP_ex5/")
    tokenized_train, tokenized_test = tokenizer(x_train, padding='longest', truncation=True), tokenizer(x_test, padding='longest', truncation=True)
    train_dataset = Dataset(encodings=tokenized_train, labels=y_train)
    test_dataset = Dataset(encodings=tokenized_test, labels=y_test)
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics
    )

    trainer.train()
    accuracy = trainer.evaluate()
    print(accuracy)

    # see https://huggingface.co/docs/transformers/v4.25.1/en/quicktour#trainer-a-pytorch-optimized-training-loop
    # Use the DataSet object defined above. No need for a DataCollator

    return accuracy


# Q3
def zeroshot_classification(portion=1.):
    """
    Perform zero-shot classification
    :param portion: portion of the data to use
    :return: classification accuracy
    """
    from transformers import pipeline
    from sklearn.metrics import accuracy_score
    import torch
    x_train, y_train, x_test, y_test = get_data(categories=category_dict.keys(), portion=portion)
    clf = pipeline("zero-shot-classification",
                   model='cross-encoder/nli-MiniLM2-L6-H768',
                   device=torch.device('cuda:0' if torch.cuda.is_available() else 'cpu'))
    candidate_labels = list(category_dict.values())


    # Add your code here
    # see https://huggingface.co/docs/transformers/v4.25.1/en/main_classes/pipelines#transformers.ZeroShotClassificationPipeline
    y_labels = np.array(candidate_labels)[y_test]
    clf_output = clf(x_test, candidate_labels)
    predicted_labels = [c['labels'][0] for c in clf_output]
    acc = accuracy_score(y_labels, predicted_labels)
    return acc


def main():
    portions = [0.1, 0.5, 1.]
    # Q1
    # p 0.1: 0.7208222811671088
    # p 0.5: 0.8103448275862069
    # p 1: 0.8275862068965517
    print("Logistic regression results:")
    acc_p_1 = []
    plt.figure()
    for p in portions:
        print(f"Portion: {p}")
        acc_p = linear_classification(p)
        acc_p_1.append(acc_p)
        plt.scatter(p, acc_p, color='teal')
        print(acc_p)
    plt.title('Model #1: accuracy as a function of portions')
    plt.plot(portions, acc_p_1, color='lightseagreen', label='accuracy')
    plt.xlabel('portion')
    plt.ylabel('accuracy')
    plt.legend()
    plt.show()

    # Q2
    # Finetuning:
    # p 0.1: 0.8587533156498673
    # p 0.5: 0.8978779840848806
    # p 1: 0.9091511936339522
    acc_p_2 = []
    print("\nFinetuning results:")
    for p in portions:
        print(f"Portion: {p}")
        acc_p = transformer_classification(portion=p)
        acc_p_2.append(acc_p)
        plt.scatter(p, acc_p, color='rebeccapurple')
        print(acc_p)
    plt.title('Model #2: accuracy as a function of portions')
    plt.plot(portions, acc_p_2, color='mediumpurple', label='accuracy')
    plt.xlabel('portion')
    plt.ylabel('accuracy')
    plt.legend()
    plt.show()

    # Q3
    # Zero Shot Classification:
    # 0.7712201591511937
    print("Zero Shot classification:")
    acc_p_3 = []
    plt.figure()
    for p in portions:
        print(f"Portion: {p}")
        acc_p = zeroshot_classification(p)
        acc_p_3.append(acc_p)
        plt.scatter(p, acc_p, color='tomato')
        print(acc_p)
    plt.title('Model #3: accuracy as a function of portions')
    plt.plot(portions, acc_p_3, color='lightsalmon', label='accuracy')
    plt.xlabel('portion')
    plt.ylabel('accuracy')
    plt.legend()
    plt.show()

main()
