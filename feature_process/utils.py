import cv2
import numpy as np
from skimage.feature import local_binary_pattern

from .lmfilter import make_lmfilter

class Utils():
    def __init__(self, rgb, rlist, rmat):
        self.height = rmat.shape[0] 
        self.width = rmat.shape[1]
        self.num_reg = len(rlist)
        self.rlist = rlist
        self.rmat = rmat
        self.rgb = rgb
        self.lab = self.get_lab()
        self.hsv = self.get_hsv()
        self.coord = self.get_coord()
        self.color_var, self.color_avg = self.get_color_var()
        self.tex_var, self.tex_avg, self.tex = self.get_tex_var()
        self.lbp_var, self.lbp = self.get_lbp_var()
        self.edge_nums = self.get_edge_nums()
        self.neigh_areas = self.get_neigh_areas()
        self.w = self.get_w()
        self.a = self.get_a()
        self.blist = self.get_background()

    def get_lab(self):
        lab = cv2.cvtColor(self.rgb, cv2.COLOR_RGB2Lab)
        return lab

    def get_hsv(self):
        hsv = cv2.cvtColor(self.rgb, cv2.COLOR_RGB2HSV)
        return hsv

    def get_coord(self):
        num_reg = self.num_reg
        coord = np.zeros([num_reg, 7])
        EPS = 1. 
        for i in range(num_reg):
            sum_y_x = np.sum(np.array(self.rlist[i]), axis=1)
            num_pix = len(self.rlist[i][0])
            coord[i][0:2] = sum_y_x // num_pix
            coord[i][0] /= self.height 
            coord[i][1] /= self.width 
            sortbyy = sorted(self.rlist[i][0])
            sortbyx = sorted(self.rlist[i][1])
            tenth = int(num_pix*0.1)
            ninetith = int(num_pix*0.9)
            coord[i][2:4] = [sortbyy[tenth]/self.height, sortbyx[tenth]/self.width]
            coord[i][4:6] = [sortbyy[ninetith]/self.height, sortbyx[ninetith]/self.width]
            a = float(sortbyy[-1] - sortbyy[0])
            b = float(sortbyx[-1] - sortbyx[0] + EPS)
            ratio = a/b
            coord[i][6] = ratio
        return coord

    def get_color_var(self):
        num_reg = self.num_reg
        avg = np.zeros([num_reg, 9])
        var = np.zeros([num_reg, 9])
        imgchan = np.concatenate([self.rgb, self.lab, self.hsv], axis=2)
        for i in range(num_reg):
            num_pix = len(self.rlist[i][0])
            avg[i, :] = np.sum(imgchan[self.rlist[i][0], self.rlist[i][1]]) / num_pix
            var[i, :] = np.sum((imgchan[self.rlist[i][0], self.rlist[i][1]] - avg[i, :])**2)/num_pix
        return var, avg

    def get_tex_var(self):
        num_reg = self.num_reg
        avg = np.zeros([num_reg, 15])
        var = np.zeros([num_reg, 15])
        ml_fiters = self.ml_kernal()
        gray = cv2.cvtColor(self.rgb, cv2.COLOR_RGB2GRAY)
        gray = gray.astype(np.float) / 255.0
        tex = np.zeros([gray.shape[0], gray.shape[1], 15])
        for i in range(15):
            tex[:, :, i] = cv2.filter2D(gray, cv2.CV_64F, ml_fiters[:,:,i])
        for i in range(num_reg):
            num_pix = len(self.rlist[i][0])
            avg[i] = np.sum(tex[self.rlist[i][0], self.rlist[i][1]])/num_pix
            var[i] = np.sum((tex[self.rlist[i][0], self.rlist[i][1]] - avg[i])**2)/num_pix
        for i in range(15):
            tex_max = np.max(tex[:,:,i])
            tex_min = np.min(tex[:,:,i])
            tex[:,:,i] = (tex[:,:,i] - tex_min)/(tex_max - tex_min) * 255
        tex = tex.astype(np.int8)
        return var, avg, tex

    def get_lbp_var(self):
        num_reg = self.num_reg
        avg = np.zeros([num_reg, 1])
        var = np.zeros([num_reg, 1])
        gray = cv2.cvtColor(self.rgb, cv2.COLOR_RGB2GRAY)
        lbp = local_binary_pattern(gray, 8, 1.) 
        for i in range(num_reg):
            num_pix = len(self.rlist[i][0])
            avg[i] = np.sum(lbp[self.rlist[i]])/num_pix
            var[i] = np.sum((lbp[self.rlist[i]] - avg[i])**2)/num_pix
        return var, lbp.astype(np.int32)

    def get_edge_nums(self):
        num_reg = self.num_reg
        edge_nums = np.zeros([num_reg, 1])
        for i in range(num_reg):
            num_pix = len(self.rlist[i][0])
            for j in range(num_pix):
                y = self.rlist[i][0][j]
                x = self.rlist[i][1][j]
                if x==0 or x==(self.width-1) or y==0 or y==(self.height-1):
                    edge_nums[i] += 1
                else:
                    is_edge = self.rmat[y, x] != self.rmat[y-1, x] or self.rmat[y,x] != self.rmat[y+1, x] or self.rmat[y, x]!=self.rmat[y, x-1] or self.rmat[y,x]!=self.rmat[y,x+1]
                    if is_edge:
                        edge_nums[i] += 1
        edge_nums /= self.width*self.height
        return edge_nums
    
    def get_neigh_areas(self):
        num_reg = self.num_reg
        neigh_areas = np.zeros([num_reg,1])
        sigmadist = 0.4
        for i in range(num_reg):
            for j in range(num_reg):
                diff = (self.coord[i][0:2] - self.coord[j][0:2])**2
                diff = np.sum(diff)
                neigh_areas[i] += np.exp(-1*diff/sigmadist)
        neigh_areas /= self.width*self.height 
        return neigh_areas

    def get_w(self):
        num_reg = self.num_reg
        pos = np.zeros([num_reg, 2])
        for i in range(num_reg):
            reg_array = np.array(self.rlist[i])
            pos[i, :] = np.sum(reg_array, axis=1) / reg_array.shape[1]
        w = np.zeros([num_reg, num_reg])
        for i in range(num_reg):
            for j in range(num_reg):
                diff = (pos[i]- pos[j])**2
                diff = np.sum(diff)
                w[i, j] = np.exp( -1. * diff / 2)
        return w

    def get_a(self):
        a = np.zeros([self.num_reg, 1] )
        a[:, 0] = [float(len(r))/float(self.width*self.height) for r in self.rlist]
        return np.array(a)

    def get_background(self):
        blist = [(),()]
        y = [y_ for y_ in range(15)] + [y_ for y_ in range(self.height-15, self.height)]
        x = [x_ for x_ in range(self.weight)]
        for y_ in y:
            for x_ in x:
                blist[0] += (y_,)
                blist[1] += (x_,)
        y = [y_ for y_ in range(15, self.height - 15)]
        x = [x_ for x_ in range(15)] + [x_ for x_ in range(self.weight-15, self.weight)]
        for y_ in y:
            for x_ in x:
                blist[0] += (y_,)
                blist[1] += (x_,)
        return [blist]
    
    def ml_kernal(self):
        ml_filters = np.zeros([49,49,15])
        ml_filters = make_lmfilter()[:,:,0:15]
        return ml_filters

    def get_diff(self, array):
        num_reg = array.shape[0]
        mat = np.zeros([num_reg, num_reg])
        for i in range(num_reg):
            for j in range(num_reg):
                mat[i][j] = np.abs(array[i] - array[j])
        return mat

    def get_diff_hist(self, color):
        num_reg = self.num_reg
        hist = np.ones([num_reg, 256])
        for i in range(num_reg):
            hist[i][color[self.rlist[i][0], self.rlist[i][1]]] += 1
        mat = np.zeros([num_reg, num_reg])
        for i in range(num_reg):
            for j in range(num_reg):
                a = 2 * (hist[i] - hist[j])**2
                b = hist[i] + hist[j] + 1.
                mat[i][j] = np.sum(a/b)
        return mat
    
    def dot(self, x, hist=False, bkg=False):
        if hist:
            diff = self.get_diff_hist(x)
        else:
            diff = self.get_diff(x)
        x = self.w * diff
        if bkg:
            x = x[-1]
        else:
            x = np.sum(x, axis=1)
        x = x * self.a[0]
        return x
