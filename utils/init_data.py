import sys
sys.path.append("./data/cocoapi/PythonAPI/")
#sys.path.append('../')
import os
import json
import numpy as np
import pickle
import cv2
from tqdm import tqdm
from config import cfg
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

class MSCOCO():
    def __init__(self,split):
        data_dir   = cfg.data_dir
        result_dir = cfg.result_dir
        cache_dir  = cfg.cache_dir

        self._split = split
        self._dataset = {
            "trainval": "trainval2014",
            "minival": "minival2014",
            "testdev": "testdev2017"
        }[self._split]

        self._coco_dir = os.path.join(data_dir, "coco")

        self._label_dir  = os.path.join(self._coco_dir, "annotations")
        self._label_file = os.path.join(self._label_dir, "instances_{}.json")
        self._label_file = self._label_file.format(self._dataset)

        self._image_dir  = os.path.join(self._coco_dir, "images", self._dataset)
        self._image_file = os.path.join(self._image_dir, "{}")

        self._data = "coco"
        self._mean = np.array([0.40789654, 0.44719302, 0.47026115], dtype=np.float32)
        self._std  = np.array([0.28863828, 0.27408164, 0.27809835], dtype=np.float32)
        self._eig_val = np.array([0.2141788, 0.01817699, 0.00341571], dtype=np.float32)
        self._eig_vec = np.array([
            [-0.58752847, -0.69563484, 0.41340352],
            [-0.5832747, 0.00994535, -0.81221408],
            [-0.56089297, 0.71832671, 0.41158938]
        ], dtype=np.float32)

        self._cat_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120] 
        
        self._classes = {
            ind + 1: cat_id for ind, cat_id in enumerate(self._cat_ids)
        }
        self._coco_to_class_map = {
            value: key for key, value in self._classes.items()
        }

        self._cache_file = os.path.join(cache_dir, "coco_{}.pkl".format(self._dataset))
        self._load_data()
        self._db_inds = np.arange(len(self._image_ids))

        self._load_coco_data()


    def _load_data(self):
        print("loading from cache file: {}".format(self._cache_file))
        if not os.path.exists(self._cache_file):
            print("No cache file found...")
            self._extract_data()
            with open(self._cache_file, "wb") as f:
                pickle.dump([self._detections, self._image_ids], f)#self._image_ids is img's name.self._detections is {name:box and cat([N,5])}
        else:
            with open(self._cache_file, "rb") as f:
                self._detections, self._image_ids = pickle.load(f)
        # count=0
        # for i in self._image_ids:
        #     if 'val' in i:
        #         print(i)
        #         im=cv2.imread('/home/makalo/workspace/code/corner_net/data/coco/images/minival2014/'+i)
        #         cv2.imwrite('/home/makalo/workspace/code/corner_net/data/coco/images/trainval2014/'+i,im)


    def _load_coco_data(self):
        self._coco = COCO(self._label_file)
        with open(self._label_file, "r") as f:
            data = json.load(f)

        coco_ids = self._coco.getImgIds()
        eval_ids = {
            self._coco.loadImgs(coco_id)[0]["file_name"]: coco_id
            for coco_id in coco_ids
        }

        self._coco_categories = data["categories"]
        self._coco_eval_ids   = eval_ids

    def class_name(self, cid):
        cat_id = self._classes[cid]
        cat    = self._coco.loadCats([cat_id])[0]
        return cat["name"]

    def _extract_data(self):
        self._coco    = COCO(self._label_file)
        self._cat_ids = self._coco.getCatIds()

        coco_image_ids = self._coco.getImgIds()

        self._image_ids = [
            self._coco.loadImgs(img_id)[0]["file_name"]
            for img_id in coco_image_ids
        
        ]
        self._detections = {}
        for ind, (coco_image_id, image_id) in enumerate(tqdm(zip(coco_image_ids, self._image_ids))):
            image      = self._coco.loadImgs(coco_image_id)[0]
            bboxes     = []
            categories = []

            for cat_id in self._cat_ids:
                annotation_ids = self._coco.getAnnIds(imgIds=image["id"], catIds=cat_id)
                annotations    = self._coco.loadAnns(annotation_ids)
                category       = self._coco_to_class_map[cat_id]
                for annotation in annotations:
                    bbox = np.array(annotation["bbox"])
                    bbox[[2, 3]] += bbox[[0, 1]]
                    bboxes.append(bbox)

                    categories.append(category)

            bboxes     = np.array(bboxes, dtype=float)
            categories = np.array(categories, dtype=float)
            if bboxes.size == 0 or categories.size == 0:
                self._detections[image_id] = np.zeros((0, 5), dtype=np.float32)
            else:
                self._detections[image_id] = np.hstack((bboxes, categories[:, None]))#each image's all boxes and box's cat [N,4]
    def get_all_img(self):
        return self._image_ids
    def read_img(self,img_name):
        img_name = img_name.decode('utf-8')
        img_path =self._image_file.format(img_name)
        img_path += '.jpg'
        img=cv2.imread(img_path)
        return img.astype(np.float32)
    def detections(self, img_name):
        detections = self._detections[bytes.decode(img_name)]

        return detections.astype(float).copy()

    def _to_float(self, x):
        return float("{:.2f}".format(x))

    def convert_to_coco(self, all_bboxes):
        detections = []
        for image_id in all_bboxes:
            coco_id = self._coco_eval_ids[image_id]
            for cls_ind in all_bboxes[image_id]:
                category_id = self._classes[cls_ind]
                for bbox in all_bboxes[image_id][cls_ind]:
                    bbox[2] -= bbox[0]
                    bbox[3] -= bbox[1]

                    score = bbox[4]
                    bbox  = list(map(self._to_float, bbox[0:4]))

                    detection = {
                        "image_id": coco_id,
                        "category_id": category_id,
                        "bbox": bbox,
                        "score": float("{:.2f}".format(score))
                    }

                    detections.append(detection)
        return detections

    def evaluate(self, result_json, cls_ids, image_ids, gt_json=None):
        if self._split == "testdev":
            return None

        coco = self._coco if gt_json is None else COCO(gt_json)

        eval_ids = [self._coco_eval_ids[image_id] for image_id in image_ids]
        cat_ids  = [self._classes[cls_id] for cls_id in cls_ids]

        coco_dets = coco.loadRes(result_json)
        coco_eval = COCOeval(coco, coco_dets, "bbox")
        coco_eval.params.imgIds = eval_ids
        coco_eval.params.catIds = cat_ids
        coco_eval.evaluate()
        coco_eval.accumulate()
        coco_eval.summarize()
        return coco_eval.stats[0], coco_eval.stats[12:]
